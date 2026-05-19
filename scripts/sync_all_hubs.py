import os
import re


def get_file_description(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r"^description:\s*(.*)", content, re.MULTILINE)
            if match:
                return match.group(1).strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""


def sync_hubs():
    wiki_dir = "wiki"
    hub_map = {
        "Business-Hub.md": "business",
        "Communication-Hub.md": "communication",
        "Updating-Hub.md": "updating",
        "Self-Hub.md": "self",
        "人际关系-Hub.md": "relationship",
        "Leadership-Hub.md": "leadership",
    }

    for hub_file, sub_dir in hub_map.items():
        hub_path = os.path.join(wiki_dir, hub_file)
        target_dir = os.path.join(wiki_dir, sub_dir)

        if not os.path.exists(hub_path) or not os.path.exists(target_dir):
            continue

        all_files = [f for f in os.listdir(target_dir) if f.endswith(".md")]
        all_files.sort()

        with open(hub_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract existing links
        existing_links = set(re.findall(r"\[\[(.*?)\]\]", content))

        # Build new list of files missing from the hub
        missing_files = []
        for file in all_files:
            name = os.path.splitext(file)[0]
            if name not in existing_links:
                desc = get_file_description(os.path.join(target_dir, file))
                summary = f": {desc}" if desc else ""
                missing_files.append(f"- [[{name}]]{summary}\n")

        if missing_files:
            # Append missing files under an "Other Files" section
            with open(hub_path, "a", encoding="utf-8") as f:
                if "\n## Other Files\n" not in content:
                    f.write("\n## Other Files\n")
                f.writelines(missing_files)
            print(f"Added {len(missing_files)} missing files to {hub_file}.")


if __name__ == "__main__":
    sync_hubs()
