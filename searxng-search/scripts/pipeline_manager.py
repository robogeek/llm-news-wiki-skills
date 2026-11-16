#!/usr/bin/env python3
import argparse
import sys
import os
import subprocess
from datetime import datetime

# We need to import CheckpointManager, which is in ../utils/checkpoint.py
# But since we are running this from 'scripts/', we can just import it if we add 'scripts' to path
# or if we are in 'scripts/' we can do 'from utils.checkpoint import CheckpointManager' 
# if 'scripts' is in PYTHONPATH.
# To be safe, let's just add the parent directory to sys.path if needed, 
# but here we are in 'scripts/' so 'utils' is a sibling of 'scripts' if we are in the root.
# The structure is:
# skills/searxng-search/
#   ├── scripts/
#   │   ├── pipeline_manager.py
#   │   └── pipeline/
#   │       └── stage_*.py
#   └── utils/
#       └── checkpoint.py

# Since we'll be running from 'scripts/', we need to add the root of the skill to sys.path
# to allow 'from utils.checkpoint import CheckpointManager'
SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, SKILL_ROOT)

try:
    from utils.checkpoint import CheckpointManager
except ImportError as e:
    print(f"Error importing CheckpointManager: {e}")
    print(f"SKILL_ROOT is: {SKILL_ROOT}")
    sys.exit(1)

# Define the stages
STAGES = {
    1: "Plan",
    2: "Search",
    3: "Triage",
    4: "Architect",
    5: "Execute"
}

def main():
    parser = argparse.ArgumentParser(description="SearXNG Search Pipeline Manager")
    parser.add_argument("topic", help="The search topic")
    parser.add_argument("--stage", type=int, choices=STAGES.keys(), help="Start from a specific stage")
    parser.add_argument("--resume", action="store_true", help="Resume from the last completed stage")
    
    # Pass through arguments for the search/pipeline
    parser.add_argument("-c", "--category", default="general", choices=["general", "news", "videos", "it", "science", "social media"])
    parser.add_argument("-l", "--language", action="append", default=[])
    parser.add_argument("--site", action="append", default=[])
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--time-range", choices=["day", "week", "month", "year"])
    parser.add_argument("--exact", action="store_true")
    parser.add_argument("--base-url", default="https://searxng-ai-nuc3.tailbedcb3.ts.net")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--sleep", type=float, default=3.0)
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")
    cm = CheckpointManager()
    checkpoint_dir = cm.initialize_session(args.topic, date_str)
    print(f"[*] Session initialized at: {checkpoint_dir}")

    # Determine starting stage
    if args.resume:
        start_stage = cm.get_last_completed_stage(args.topic, date_str) + 1
        if start_stage > 5:
            print("[!] Pipeline already completed.")
            sys.exit(0)
        print(f"[*] Resuming from stage {start_stage} ({STAGES[start_stage]})")
    elif args.stage:
        start_stage = args.stage
        print(f"[*] Starting from stage {start_stage} ({STAGES[start_stage]})")
    else:
        start_stage = 1
        print(f"[*] Starting new pipeline at stage 1 (Plan)")

    current_stage = start_stage
    while current_stage <= 5:
        stage_name = STAGES[current_stage]
        print(f"\n>>> Running Stage {current_stage}: {stage_name}")
        
        worker_script = os.path.join(os.path.dirname(__file__), "pipeline", f"stage_{current_stage:02d}.py")
        
        if not os.path.exists(worker_script):
            print(f"[!] Worker script not found: {worker_script}")
            sys.exit(1)

        # Build the command
        cmd = [
            sys.executable, worker_script,
            "--topic", args.topic,
            "--date_str", date_str,
            "--category", args.category,
            "--pages", str(args.pages),
            "--base_url", args.base_url,
            "--timeout", str(args.timeout),
            "--retries", str(args.retries),
            "--sleep", str(args.sleep),
        ]
        
        if args.language:
            cmd.extend(["--languages", ",".join(args.language)])
        if args.site:
            cmd.extend(["--sites", ",".join(args.site)])
        if args.time_range:
            cmd.extend(["--time_range", args.time_range])
        if args.exact:
            cmd.append("--exact")
        
        cmd.extend(["--output_format", "json" if args.json else "text"])

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                # We might want to show stderr if it's not just warnings
                print("--- stderr ---")
                print(result.stderr)
            
            current_stage += 1
        except subprocess.CalledProcessError as e:
            print(f"\n[!] Error in stage {current_stage} ({stage_name}):")
            print(e.stdout)
            print(e.stderr)
            print(f"\n[!] Pipeline halted at stage {current_stage}. Use --resume to try again.")
            sys.exit(1)

    print("\n[+] Pipeline completed successfully.")

if __name__ == "__main__":
    main()
