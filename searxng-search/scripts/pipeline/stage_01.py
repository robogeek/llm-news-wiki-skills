#!/usr/bin/env python3
import argparse
import os
import sys
import json
from datetime import datetime

# Add skill root to sys.path to allow importing utils
SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, SKILL_ROOT)

try:
    from utils.checkpoint import CheckpointManager
except ImportError as e:
    print(f"Error importing CheckpointManager: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Stage 1: Plan")
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

    # Build the plan
    plan = {
        "topic": args.topic,
        "date_created": args.date_str,
        "search_params": {
            "query_terms": args.topic, # In a real scenario, we might refine this
            "category": args.category,
            "languages": args.languages.split(",") if args.languages else [],
            "sites": args.sites.split(",") if args.sites else [],
            "pages": args.pages,
            "time_range": args.time_range if args.time_range else None,
            "base_url": args.base_url,
            "timeout": args.timeout,
            "retries": args.retries,
            "sleep": args.sleep,
            "exact": args.exact
        }
    }

    # Save the plan
    checkpoint_path = cm.save_checkpoint(args.topic, args.date_str, 1, plan)
    print(f"[*] Plan created and saved to: {checkpoint_path}")

    if args.output_format == "json":
        print(json.dumps(plan, indent=2))
    else:
        print(f"Plan for topic: {args.topic}")
        print(f"  Category: {args.category}")
        print(f"  Languages: {plan['search_params']['languages']}")
        print(f"  Pages: {args.pages}")

if __name__ == "__main__":
    main()
