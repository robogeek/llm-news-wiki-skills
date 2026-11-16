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

def main():
    parser = argparse.ArgumentParser(description="Stage 3: Triage")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--date_str", required=True)
    parser.add_argument("--output_format", choices=["json", "text"], default="text")

    args, unknown = parser.parse_known_args()
    cm = CheckpointManager()

    # Load the results from Stage 2
    stage_2_output = cm.load_checkpoint(args.topic, args.date_str, 2)
    if not stage_2_output:
        print(f"[!] Error: Results not found. Did you run Stage 2?")
        sys.exit(1)
    
    raw_results = stage_2_output.get("results", [])
    
    # Triage: filter out invalid entries
    vetted_results = []
    for r in raw_results:
        if r.get("title") and r.get("url"):
            vetted_results.append(r)
    
    # Prepare the triage output
    triage_output = {
        "original_count": len(raw_results),
        "vetted_count": len(vetted_results),
        "results": vetted_results,
        "unresponsive": stage_2_output.get("unresponsive", []),
        "errors": stage_2_output.get("errors", [])
    }

    # Save the triage output
    checkpoint_path = cm.save_checkpoint(args.topic, args.date_str, 3, triage_output)
    print(f"[*] Triage completed and saved to: {checkpoint_path}")

    if args.output_format == "json":
        print(json.dumps(triage_output, indent=2))
    else:
        print(f"Triage Summary for topic: {args.topic}")
        print(f"  Original results: {len(raw_results)}")
        print(f"  Vetted results: {len(vetted_results)}")
        print(f"  Dropped: {len(raw_results) - len(vetted_results)}")
        print("\nTop candidates:")
        for r in vetted_results[:10]:
            print(f"- {r['title'][:70]}... | {r['url']}")

if __name__ == "__main__":
    main()
