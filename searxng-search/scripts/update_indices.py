import os
import yaml
import datetime

WIKI_ROOT = "wiki"

def get_frontmatter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    data = yaml.safe_load(parts[1])
                    return data, parts[2]
                except yaml.YAMLError:
                    return None, None
    return None, None

def update_index(directory, index_file, mode="summary"):
    files = []
    for f in sorted(os.listdir(directory)):
        if f.endswith('.md') and f != 'index.md':
            files.append(f)
    
    lines = []
    if mode == "summary":
        lines.append("# Summaries\n")
    elif mode == "concepts":
        lines.append("# Concepts\n")
    elif mode == "organizations":
        lines.append("# Organizations\n")
    elif mode == "places":
        lines.append("# Places\n")
    elif mode == "events":
        lines.append("# Events\n")
    elif mode == "people":
        lines.append("# People\n")
    elif mode == "cases":
        lines.append("# Cases\n")
    elif mode == "answers":
        lines.append("# Answers\n")
    elif mode == "timelines":
        lines.append("# Timelines\n")

    for f in files:
        path = os.path.join(directory, f)
        data, body = get_frontmatter(path)
        if data:
            title = data.get('title', f)
            summary = data.get('Summary', '')
            
            # Get date from frontmatter or filename
            date_val = data.get('date-created', 'YYYY-MM-DD')
            if isinstance(date_val, datetime.datetime):
                date_str = date_val.strftime("%Y-%m-%d")
            elif isinstance(date_val, str):
                date_str = date_val[:10]
            else:
                date_str = 'YYYY-MM-DD'
            
            if mode == "summary":
                lines.append(f"- {date_str} [{title}](./{f}) {summary}")
            else:
                lines.append(f"- [{title}](./{f})")
        else:
            lines.append(f"- [{f}](./{f})")

    with open(os.path.join(WIKI_ROOT, index_file), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")

def update_main_index():
    # The main index is manual or semi-automatic
    # For now, let's just keep it as is or rebuild it if we have a list
    pass

if __name__ == "__main__":
    # Update all indices
    update_index("wiki/summaries", "summaries/index.md", "summary")
    update_index("wiki/concepts", "concepts/index.md", "concepts")
    update_index("wiki/organizations", "organizations/index.md", "organizations")
    update_index("wiki/places", "places/index.md", "places")
    update_index("wiki/events", "events/index.md", "events")
    update_index("wiki/people", "people/index.md", "people")
    
    print("Indices updated.")
