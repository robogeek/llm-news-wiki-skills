#!/usr/bin/env python3
import argparse
import os
import sys
import json

# Add skill root to sys.path to allow importing utils
SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, SKILL_ROOT)

try:
    from utils.checkpoint import CheckpointManager
except ImportError as e:
    print(f"Error importing CheckpointManager: {e}")
    sys.exit(1)

# Simple keyword matching for "entity" detection
ORG_KEYWORDS = ["partidul", "partidul psd", "pnl", "reforma", "ministerul", "guvernul", "primaria", "compania", "societatea", "media", "digi24", "hotnews", "adevarul", "protv"]
PLACE_KEYWORDS = ["bucuresti", "constanta", "iasi", "cluj", "timisoara", "romania", "europa"]

def main():
    parser = argparse.ArgumentParser(description="Stage 4: Architect")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--date_str", required=True)
    parser.add_argument("--output_format", choices=["json", "text"], default="text")

    args, unknown = parser.parse_known_args()
    cm = CheckpointManager()

    # Load the triage output from Stage 3
    triage_output = cm.load_checkpoint(args.topic, args.date_str, 3)
    if not triage_output:
        print(f"[!] Error: Triage results not found. Did you run Stage 3?")
        sys.exit(1)
    
    vetted_results = triage_output.get("results", [])
    
    # Propose actions
    actions = []
    
    # 1. For every result, propose a summary
    for r in vetted_results:
        actions.append({
            "type": "summary",
            "url": r["url"],
            "suggested_title": r["title"],
            "description": f"Summary of article: {r['title']}"
        })
        
        # 2. Attempt to detect organizations/places from title
        title_lower = r["title"].lower()
        
        for kw in ORG_KEYWORDS:
            if kw in title_lower:
                actions.append({
                    "type": "organization",
                    "name": kw.capitalize(),
                    "description": f"Entity mentioned in: {r['url']}"
                })
                break # Only one org per article for now
                
        for kw in PLACE_KEYWORDS:
            if kw in title_lower:
                actions.append({
                    "type": "place",
                    "name": kw.capitalize(),
                    "description": f"Location mentioned in: {r['url']}"
                })
                break

    # Deduplicate actions by type and name/url
    unique_actions = []
    seen = set()
    for a in actions:
        # Create a key for deduplication
        if a["type"] == "summary":
            key = f"summary_{a['url']}"
        else:
            key = f"{a['type']}_{a['name'].lower()}"
            
        if key not in seen:
            unique_actions.append(a)
            seen.add(key)

    architectural_plan = {
        "topic": args.topic,
        "proposed_actions": unique_actions
    }

    # Save the plan
    checkpoint_path = cm.save_checkpoint(args.topic, args.date_str, 4, architectural_plan)
    print(f"[*] Architectural plan created and saved to: {checkpoint_path}")

    if args.output_format == "json":
        print(json.dumps(architectural_plan, indent=2))
    else:
        print(f"Proposed Architectural Plan for topic: {args.topic}")
        print(f"  Number of proposed actions: {len(unique_actions)}")
        print("\nProposed Actions:")
        for i, a in enumerate(unique_actions, 1):
            if a["type"] == "summary":
                print(f"{i}. [Summary] {a['suggested_title']} ({a['url']})")
            else:
                print(f"{i}. [{a['type'].capitalize()}] {a['name']}")

if __name__ == "__main__":
    main()
