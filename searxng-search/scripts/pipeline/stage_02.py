#!/usr/bin/env python3
import argparse
import os
import sys
import json
import time

# Add skill root to sys.path to allow importing utils
SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, SKILL_ROOT)

try:
    from utils.checkpoint import CheckpointManager
    from utils.searxng_client import fetch, build_query, resolve_lang
except ImportError as e:
    print(f"Error importing utilities: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Stage 2: Search")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--date_str", required=True)
    parser.add_argument("--category", default="general")
    parser.add_argument("--languages", default="")
    parser.add_argument("--sites", default="")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--time_range", default="")
    parser.add_argument("--base_url", default="")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--sleep", type=float, default=3.0)
    parser.add_argument("--exact", action="store_true")
    parser.add_argument("--output_format", choices=["json", "text"], default="text")

    args, unknown = parser.parse_known_args()
    cm = CheckpointManager()

    # Load the plan from Stage 1
    plan = cm.load_checkpoint(args.topic, args.date_str, 1)
    if not plan:
        print(f"[!] Error: Plan not found. Did you run Stage 1?")
        sys.exit(1)
    
    search_params = plan["search_params"]
    # Use parameters from the plan, but allow overrides from command line if needed? 
    # Actually, for a pipeline, we should strictly follow the plan.
    
    q = build_query(args.topic, args.sites.split(",") if args.sites else [], args.exact)
    langs = [resolve_lang(l) for l in (args.languages.split(",") if args.languages else [""])]
    if not langs or langs == [""]:
        langs = [None]

    merged = {}  # url -> result
    unresponsive = set()
    errors = []

    for lang in langs:
        for page in range(1, args.pages + 1):
            params = {
                "q": q,
                "format": "json",
                "categories": args.category,
                "pageno": page
            }
            if lang:
                params["language"] = lang
            if args.time_range:
                params["time_range"] = args.time_range
            if args.base_url:
                params["base_url"] = args.base_url

            data = None
            for attempt in range(1, args.retries + 1):
                try:
                    data = fetch(args.base_url or "https://searxng-ai-nuc3.tailbedcb3.ts.net", params, args.timeout)
                    break
                except Exception as e:
                    errors.append(f"[{lang or 'all'}/p{page}] attempt {attempt}: {e}")
                    if attempt < args.retries:
                        time.sleep(args.sleep)
            
            if data is None:
                continue

            for eng, _reason in data.get("unresponsive_engines", []):
                unresponsive.add(eng)
            
            for r in data.get("results", []):
                url = r.get("url") or ""
                if not url or url in merged:
                    continue
                merged[url] = {
                    "title": (r.get("title") or "").strip(),
                    "url": url,
                    "date": (r.get("publishedDate") or "")[:10],
                    "engine": r.get("engine", ""),
                    "lang": lang or "",
                    "page": page,
                }

    results = sorted(merged.values(), key=lambda r: (r["lang"], r["page"]))
    
    stage_output = {
        "query": q,
        "category": args.category,
        "languages": langs,
        "count": len(results),
        "unresponsive": sorted(unresponsive),
        "errors": errors,
        "results": results
    }

    # Save the results
    checkpoint_path = cm.save_checkpoint(args.topic, args.date_str, 2, stage_output)
    print(f"[*] Search results saved to: {checkpoint_path}")

    if args.output_format == "json":
        print(json.dumps(stage_output, indent=2))
    else:
        print(f"# Results for query: {q}")
        print(f"Count: {len(results)} | Unresponsive: {len(unresponsive)}")
        for r in results:
            print(f"- {r['date'] or '----------'} | {r['title'][:90]} | {r['url']}")

if __name__ == "__main__":
    main()
