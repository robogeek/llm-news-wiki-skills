#!/usr/bin/env python3
import argparse
import os
import sys
import json
import urllib.request
import datetime

# Add skill root to sys.path to allow importing utils
SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, SKILL_ROOT)

try:
    from utils.checkpoint import CheckpointManager
except ImportError as e:
    print(f"Error importing CheckpointManager: {e}")
    sys.exit(1)

def fetch_content(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Stage 5: Execute")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--date_str", required=True)
    parser.add_argument("--output_format", choices=["json", "text"], default="text")

    args, unknown = parser.parse_known_args()
    cm = CheckpointManager()

    # Load the plan from Stage 4
    plan = cm.load_checkpoint(args.topic, args.date_str, 4)
    if not plan:
        print(f"[!] Error: Plan not found. Did you run Stage 4?")
        sys.exit(1)
    
    actions = plan.get("proposed_actions", [])
    
    completed_actions = []
    failed_actions = []

    # Ensure wiki directories exist
    for directory in ["wiki/summaries", "wiki/organizations", "wiki/places", "wiki/events", "wiki/people"]:
        os.makedirs(directory, exist_ok=True)

    for action in actions:
        print(f"[*] Executing: {action['type']} - {action.get('name') or action.get('suggested_title')}")
        
        try:
            if action["type"] == "summary":
                url = action["url"]
                title = action["suggested_title"]
                content = fetch_content(url)
                
                if content:
                    # Create summary file
                    filename = f"summary_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.md"
                    # For demo, we just write the first 500 chars
                    summary_content = f"---\ntitle: \"Summary of {title}\"\nSummary: \"Automated summary from search pipeline.\"\nSources:\n  - {url}\ntype: summary\ndate-created: {args.date_str}\nlast-updated: {args.date_str}\n---\n\n{content[:500]}..."
                    
                    path = os.path.join("wiki/summaries", filename)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(summary_content)
                    
                    completed_actions.append({"type": "summary", "url": url, "path": path})
                else:
                    failed_actions.append({"type": "summary", "url": url, "reason": "Failed to fetch content"})

            elif action["type"] in ["organization", "place"]:
                # For demo, just create an empty page
                name = action["name"]
                filename = f"{name.lower().replace(' ', '_')}.md"
                path = os.path.join(f"wiki/{action['type']}s", filename)
                
                summary_content = f"---\ntitle: \"{name}\"\nSummary: \"Automated entity creation from search pipeline.\"\nType: {action['type']}\ndate-created: {args.date_str}\nlast-updated: {args.date_str}\n---\n\nEntity: {name}"
                
                with open(path, "w", encoding="utf-8") as f:
                    f.write(summary_content)
                
                completed_actions.append({"type": action["type"], "name": name, "path": path})

        except Exception as e:
            print(f"    [!] Failed: {e}")
            failed_actions.append({"type": action["type"], "reason": str(e)})

    # Save the execution summary
    execution_summary = {
        "topic": args.topic,
        "completed": completed_actions,
        "failed": failed_actions
    }
    
    checkpoint_path = cm.save_checkpoint(args.topic, args.date_str, 5, execution_summary)
    print(f"[*] Execution summary saved to: {checkpoint_path}")

    if args.output_format == "json":
        print(json.dumps(execution_summary, indent=2))
    else:
        print(f"\nExecution Results for topic: {args.topic}")
        print(f"  Completed: {len(completed_actions)}")
        print(f"  Failed: {len(failed_actions)}")

if __name__ == "__main__":
    main()
