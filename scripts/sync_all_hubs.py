import logging
import os
import re
import shutil
from pathlib import Path

import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


# Load .env
load_env(Path(__file__).parent.parent / ".env")
WORKSPACE_PATH = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)


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


def get_yaml_field(content, field):
    match = re.search(rf"^{field}:\s*(.*)", content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return None


def sync_hubs():
    self_wiki_dir = WORKSPACE_PATH / "self-wiki"
    wiki_dir = self_wiki_dir / "wiki"

    # Hub definition: Filename -> (Tag to match, Subdirectory, Display Title)
    hub_map = {
        "Business-Hub.md": ("business", "business", "商业与职业"),
        "Communication-Hub.md": ("communication", "communication", "沟通与表达"),
        "Updating-Hub.md": ("updating", "updating", "其他杂项"),
        "Self-Hub.md": ("self", "self", "自我认知"),
        "人际关系-Hub.md": ("relationship", "relationship", "人际关系"),
        "Leadership-Hub.md": ("leadership", "leadership", "领导力"),
    }

    # 1. Ensure hubs exist
    tag_to_files = {}
    for tag, subdir, title in hub_map.values():
        tag_to_files[tag] = []

    for hub_file, (tag, subdir, hub_title) in hub_map.items():
        hub_path = wiki_dir / hub_file
        if not hub_path.exists():
            hub_path.write_text(
                f"---\ntitle: {hub_title}\ndescription: Thematic hub for {tag}.\nlevel: 1\ntags: [hub]\n---\n\n# {hub_title}\n\n",
                encoding="utf-8",
            )
            logger.info(f"Created missing hub file: {hub_file}")

    # 2. Scan all files in wiki directory
    for file_path in wiki_dir.rglob("*.md"):
        # Ignore hub files, index, and audit
        if file_path.name in hub_map or file_path.name in ["INDEX.md", "audit.md"]:
            continue

        content = file_path.read_text(encoding="utf-8")
        # Extract tags using YAML parsing
        try:
            fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm = yaml.safe_load(fm_match.group(1))
                tags = fm.get("tags", [])
            else:
                tags = []
        except:
            tags = []

        target_tag = None
        for tag in tags:
            # Handle potential nested structures
            clean_tag = str(tag).split("/")[-1]
            if clean_tag in tag_to_files:
                target_tag = clean_tag
                break

        if target_tag:
            # Map tag back to the subdir from hub_map
            subdir = next(item[1] for item in hub_map.values() if item[0] == target_tag)
            target_subdir = wiki_dir / subdir
            if not target_subdir.exists():
                target_subdir.mkdir(parents=True, exist_ok=True)

            # Move file if it's not already in the target directory
            if file_path.parent != target_subdir:
                new_path = target_subdir / file_path.name
                shutil.move(str(file_path), str(new_path))
                logger.info(f"Moved {file_path.name} to {target_subdir.name}/")
                file_path = new_path

            tag_to_files[target_tag].append(file_path)

    # 3. Update each Hub
    for hub_file, (tag, subdir, hub_title) in hub_map.items():
        hub_path = wiki_dir / hub_file
        files_to_add = tag_to_files.get(tag, [])

        with open(hub_path, "r", encoding="utf-8") as f:
            content = f.read()

        missing_files = []
        for file_path in files_to_add:
            name = file_path.stem
            # Link using the new directory structure
            rel_subdir = file_path.parent.name
            link_ref = f"[[{rel_subdir}/{name}]]"
            if f"[[{name}]]" not in content and link_ref not in content:
                desc = get_file_description(file_path)
                summary = f": {desc}" if desc else ""
                missing_files.append(f"- {link_ref}{summary}\n")

        if missing_files:
            if "\n## Other Files\n" not in content:
                content += "\n## Other Files\n"
            with open(hub_path, "a", encoding="utf-8") as f:
                f.writelines(missing_files)
            logger.info(f"Added {len(missing_files)} new entries to {hub_file}.")


if __name__ == "__main__":
    sync_hubs()
