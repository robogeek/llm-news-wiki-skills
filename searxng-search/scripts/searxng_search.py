#!/usr/bin/env python3
"""Query the SearXNG instances' JSON API across categories, languages and pages.

Built for the searxng-search skill (shared news-wiki toolkit). Merges and dedupes
results, reports unresponsive engines, and normalizes output for vetting.

Instances (verified 16 November 2026):

  primary  https://searxng-ai-nuc3.tailbedcb3.ts.net   (JSON API enabled)
  second   https://searxng-ai.tailbedcb3.ts.net   (JSON API enabled)
  openserp https://openserp.tailbedcb3.ts.net          (/health lists engines)

Fallback chain - each stage runs only when everything before it produced zero
results (--no-fallback stops after stage 1):

  1. Normal SearXNG query on the primary (--base-url).
  2. Same query on the second instance (--alt-base-url): catches a down or
     degraded primary.
  3. Engine-routed retry on each instance (added 29 October 2026, after a
     session in which the four big general engines were runtime-suspended):
     an engine allowlist that skips the usually-suspended big four (brave,
     duckduckgo, google, startpage) - runtime suspensions do NOT clear on
     instance restart, but the smaller engines (bing, yahoo, yandex, seznam,
     yep, qwant) keep working.
  4. OpenSerp (--openserp-base): an independent scraper API with its own
     google/bing/duckduckgo/yandex/ecosia engines - a different index view,
     useful when SearXNG's engines are all blocked or the query shape is
     tokenized badly.

--openserp-always runs stage 4 even when SearXNG already returned results
(merged and deduped; use when coverage matters more than latency).

Examples:
  searxng_search.py "moțiunea de cenzură" Bolojan -c news -l RO
  searxng_search.py "exact phrase" -l RO --no-fallback               # single instance only
  searxng_search.py Bolojan -c news -l RO --openserp-always          # max coverage
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://searxng-ai-nuc3.tailbedcb3.ts.net"   # primary (JSON API verified)
DEFAULT_ALT_BASE = "https://searxng-ai.tailbedcb3.ts.net"   # second instance (403 until JSON enabled)
DEFAULT_OPENSERP_BASE = "https://openserp.tailbedcb3.ts.net"

CATEGORIES = ["general", "news", "videos", "it", "science", "social media"]

# Engines that keep working when brave/duckduckgo/google/startpage are
# runtime-suspended (verified 29 October 2026 on the host instance).
FALLBACK_ENGINES = "bing,yahoo,yandex,seznam,yep,qwant"

# OpenSerp engines (its /health endpoint lists google, yandex, baidu, bing,
# duckduckgo, ecosia). Response shape: a JSON list of
# {title, url, snippet, domain, engine, position, ...}.
OPENSERP_ENGINES = ["google", "bing", "duckduckgo", "yandex", "ecosia"]

# ISO 3166-1 alpha-2 country -> SearXNG locale (the country's primary language).
# SearXNG has no per-query country parameter; language is the closest handle.
COUNTRY_LANG = {
    "ro": "ro", "md": "ro", "gr": "el", "cy": "el", "bg": "bg", "hu": "hu",
    "ua": "uk", "de": "de", "at": "de", "ch": "de", "fr": "fr", "be": "fr",
    "it": "it", "es": "es", "pt": "pt", "gb": "en", "uk": "en", "ie": "en",
    "us": "en", "pl": "pl", "cz": "cs", "sk": "cs", "se": "sv", "dk": "da",
    "no": "nb", "fi": "fi", "nl": "nl", "tr": "tr", "rs": "sr", "hr": "hr",
    "si": "sl", "il": "he", "ae": "ar", "eg": "ar",
}


def build_query(terms, sites, exact):
    """Compose the q string: terms (optionally quoted) plus site: filters."""
    parts = []
    for t in terms:
        parts.append(f'"{t}"' if exact and " " in t else t)
    q = " ".join(parts)
    if sites:
        site_expr = " OR ".join(f"site:{s}" for s in sites)
        q = f"{q} {site_expr}" if q else site_expr
    return q


def fetch(base, params, timeout):
    qs = urllib.parse.urlencode(params)
    url = f"{base}/search?{qs}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; searxng-search-skill)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8", "replace")
    if "json" not in ctype:
        raise RuntimeError(
            f"non-JSON response (content-type: {ctype!r}) - wrong endpoint or "
            f"format=json disabled on the instance"
        )
    return json.loads(body)


def fetch_openserp(base, engine, params, timeout):
    """Query OpenSerp: GET {base}/{engine}/search?text=...&lang=...&limit=...

    Returns a JSON list of {title, url, snippet, ...} dicts (or an error dict).
    """
    qs = urllib.parse.urlencode(params)
    url = f"{base}/{engine}/search?{qs}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; searxng-search-skill)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8", "replace")
    if "json" not in ctype:
        raise RuntimeError(f"non-JSON response from OpenSerp {engine} (content-type: {ctype!r})")
    data = json.loads(body)
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"OpenSerp {engine}: {data.get('message') or data.get('error')}")
    return data if isinstance(data, list) else data.get("results", [])


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("terms", nargs="+", help="query terms (first is usually the phrase)")
    p.add_argument(
        "-c", "--category", default="general", choices=CATEGORIES,
        help="SearXNG category (default: general)",
    )
    p.add_argument(
        "-l", "--language", action="append", default=[],
        help="country code or locale; accepts lists ('RO,GR', 'RO GR'); "
        "repeatable; default: single unlocalized query",
    )
    p.add_argument("--site", action="append", default=[],
        help="restrict to domain (repeatable, OR-joined, engine-dependent)")
    p.add_argument("--pages", type=int, default=1, help="pages per language (default 1)")
    p.add_argument("--time-range", choices=["day", "week", "month", "year"],
        help="coarse recency filter (verify dates on the articles)")
    p.add_argument("--engines", help="comma-separated engine allowlist (e.g. 'bing,qwant')")
    p.add_argument("--exact", action="store_true",
        help="double-quote each multi-word term (phrase match)")
    p.add_argument("--base-url", default=DEFAULT_BASE,
        help=f"primary SearXNG base URL (default {DEFAULT_BASE})")
    p.add_argument("--alt-base-url", default=DEFAULT_ALT_BASE,
        help=f"second SearXNG base URL, tried when the primary fails or returns "
             f"zero results (default {DEFAULT_ALT_BASE}; pass '' to disable)")
    p.add_argument("--timeout", type=int, default=30, help="per-request timeout (s)")
    p.add_argument("--retries", type=int, default=2, help="attempts per request")
    p.add_argument("--sleep", type=float, default=3.0, help="seconds between retries")
    p.add_argument("--json", action="store_true", help="emit merged JSON")
    p.add_argument("--no-fallback", action="store_true",
        help="disable both fallbacks (engine-routed SearXNG retry and OpenSerp)")
    p.add_argument("--fallback-engines", default=FALLBACK_ENGINES,
        help=f"engine allowlist for the SearXNG engine-routed fallback (default {FALLBACK_ENGINES})")
    p.add_argument("--openserp-base", default=DEFAULT_OPENSERP_BASE,
        help=f"OpenSerp base URL (default {DEFAULT_OPENSERP_BASE})")
    p.add_argument("--openserp-engines", default=",".join(OPENSERP_ENGINES),
        help=f"comma-separated OpenSerp engines (default {','.join(OPENSERP_ENGINES)})")
    p.add_argument("--openserp-limit", type=int, default=10,
        help="results per OpenSerp engine (default 10)")
    p.add_argument("--openserp-always", action="store_true",
        help="query OpenSerp in addition to SearXNG even when SearXNG returned "
             "results (merged; use when coverage matters more than latency)")
    return p.parse_args(argv)


def resolve_lang(tag):
    if tag is None:
        return None
    t = tag.strip().lower().replace("-", "")
    if t in COUNTRY_LANG:
        return COUNTRY_LANG[t]
    return tag  # already a locale like "ro" or "en-US"


def searxng_engine_routed_fallback(base, q, langs, args, merged, unresponsive, errors, fallbacks,
                                   label="searxng-engines"):
    """Fallback: re-query a SearXNG instance with an allowlist of engines that
    skip the usually-suspended big four. Returns the number of results added."""
    before = len(merged)
    for lang in langs:
        params = {"q": q, "format": "json", "categories": args.category,
                  "pageno": 1, "engines": args.fallback_engines}
        if lang:
            params["language"] = lang
        if args.time_range:
            params["time_range"] = args.time_range
        try:
            data = fetch(base, params, args.timeout)
        except Exception as e:  # noqa: BLE001
            errors.append(f"[fallback-engines/{lang or 'all'}] {e}")
            continue
        for eng, _reason in data.get("unresponsive_engines", []):
            unresponsive.add(f"{eng} (fallback)")
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
                "page": 1,
            }
    added = len(merged) - before
    if added:
        fallbacks.append(f"{label}({args.fallback_engines}): +{added}")
    return added


def openserp_fallback(base, q, langs, args, merged, errors, fallbacks, label="openserp"):
    """Query the OpenSerp instance (independent engines). Returns the number
    of results added."""
    engines = [e.strip() for e in args.openserp_engines.split(",") if e.strip()]
    before = len(merged)
    for lang in langs:
        params = {"text": q, "limit": args.openserp_limit}
        if lang:
            params["lang"] = lang
        for engine in engines:
            try:
                items = fetch_openserp(base, engine, params, args.timeout)
            except Exception as e:  # noqa: BLE001
                errors.append(f"[openserp/{engine or '?'}/{lang or 'all'}] {e}")
                continue
            for r in items:
                url = r.get("url") or ""
                if not url or url in merged:
                    continue
                merged[url] = {
                    "title": (r.get("title") or "").strip(),
                    "url": url,
                    "date": "",
                    "engine": f"openserp:{engine}",
                    "lang": lang or "",
                    "page": 1,
                }
    added = len(merged) - before
    if added:
        fallbacks.append(f"{label}({','.join(engines)}): +{added}")
    return added


def query_instance(base, q, langs, args, merged, unresponsive, errors):
    """Run the normal pages x languages query loop against one SearXNG
    instance. Returns the number of results added to `merged`."""
    before = len(merged)
    for lang in langs:
        for page in range(1, args.pages + 1):
            params = {"q": q, "format": "json", "categories": args.category,
                      "pageno": page}
            if lang:
                params["language"] = lang
            if args.time_range:
                params["time_range"] = args.time_range
            if args.engines:
                params["engines"] = args.engines

            data = None
            for attempt in range(1, args.retries + 1):
                try:
                    data = fetch(base, params, args.timeout)
                    break
                except Exception as e:  # noqa: BLE001 - report and retry
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
    return len(merged) - before


def main(argv):
    args = parse_args(argv)
    q = build_query(args.terms, args.site, args.exact)
    raw_langs = [t for chunk in args.language for t in
                 chunk.replace(",", " ").split()] or [None]
    langs = [resolve_lang(t) for t in raw_langs]

    merged = {}  # url -> result
    unresponsive = set()
    errors = []
    fallbacks = []

    query_instance(args.base_url, q, langs, args, merged, unresponsive, errors)

    # Fallback chain (each stage only when everything before it produced
    # nothing; --openserp-always is the one exception - it always runs).
    if not merged and args.alt_base_url and not args.no_fallback:
        added = query_instance(args.alt_base_url, q, langs, args, merged,
                               unresponsive, errors)
        if added:
            fallbacks.append(f"alt-instance: +{added}")
    if not merged and not args.no_fallback:
        searxng_engine_routed_fallback(
            args.base_url, q, langs, args, merged, unresponsive, errors, fallbacks)
    if not merged and args.alt_base_url and not args.no_fallback:
        searxng_engine_routed_fallback(
            args.alt_base_url, q, langs, args, merged, unresponsive, errors,
            fallbacks, label="alt-searxng-engines")
    if args.openserp_always and not args.no_fallback:
        openserp_fallback(args.openserp_base, q, langs, args, merged, errors,
                          fallbacks, label="openserp-always")
    if not merged and not args.no_fallback:
        openserp_fallback(
            args.openserp_base, q, langs, args, merged, errors, fallbacks)

    results = sorted(merged.values(), key=lambda r: (r["lang"], r["page"]))
    if args.json:
        json.dump({"query": q, "category": args.category,
                   "languages": langs, "count": len(results),
                   "instances": [b for b in (args.base_url, args.alt_base_url) if b],
                   "unresponsive": sorted(unresponsive),
                   "fallbacks": fallbacks, "results": results},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0

    print(f"# query: {q}")
    print(f"# primary: {args.base_url}")
    print(f"# category: {args.category} | languages: {langs or ['(none)']} "
          f"| results: {len(results)}")
    if fallbacks:
        print(f"# fallbacks used: {'; '.join(fallbacks)}")
    if unresponsive:
        print(f"# unresponsive engines: {', '.join(sorted(unresponsive))}")
    if errors:
        print("# errors (retried):")
        for e in errors:
            print(f"#   {e}")
    cur_lang = None
    for r in results:
        if r["lang"] != cur_lang:
            cur_lang = r["lang"]
            print(f"\n== language: {cur_lang or '(none)'} ==")
        print(f"- {r['date'] or '----------'} | {r['title'][:90]} | {r['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
