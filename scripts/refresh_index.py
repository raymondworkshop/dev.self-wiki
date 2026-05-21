import json
import logging
import re
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_yaml_field(content, field):
    # Locate the start of the field
    match = re.search(rf"^{field}:\s*(.*)", content, re.MULTILINE)
    if match:
        # Check if it's a multi-line list block
        # Look ahead for lines starting with '-'
        block_match = re.search(
            rf"^{field}:\s*(?:.*(?:\n\s*[-*].*)*)", content, re.MULTILINE | re.DOTALL
        )
        if block_match:
            block = block_match.group(0)
            # Find all tag lines
            tags = re.findall(rf"^\s*[-*]\s*(.*)", block, re.MULTILINE)
            if tags:
                return [t.strip().strip("'\" ") for t in tags if t.strip()]

        # Fallback to single line/bracketed
        val = match.group(1).strip()
        if val.startswith("["):
            cleaned = val.strip("[]'\" ")
            return [t.strip().strip("'\" ") for t in cleaned.split(",") if t.strip()]
        return [val.strip("\"' ")]
    return None


def refresh_index():
    workspace = Path("/Users/zhaowenlong/workspace/dev.self-wiki")
    wiki_dir = workspace / "self-wiki" / "wiki"
    log_dir = workspace / "self-wiki" / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    json_index_path = log_dir / "INDEX.json"

    # Find all topics and extract metadata
    topics_data = {}
    for f in wiki_dir.rglob("*.md"):
        if f.name in ["INDEX.md", "audit.md"]:
            continue

        try:
            content = f.read_text(encoding="utf-8")
            # Extract YAML header (assuming it's between --- and ---)
            fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            fm_content = fm_match.group(1) if fm_match else content

            # Get level - handle potential non-integer values gracefully
            level_val = get_yaml_field(fm_content, "level")
            try:
                level = (
                    int(level_val[0])
                    if isinstance(level_val, list)
                    else int(level_val or 0)
                )
            except:
                level = 0

            # Get tags
            tags = get_yaml_field(fm_content, "tags") or []

            topics_data[f.stem] = {
                "path": str(f.relative_to(workspace)),
                "level": level,
                "tags": tags,
            }
        except Exception as e:
            logger.warning(f"Failed to index {f.name}: {e}")
            continue

    # Build JSON map
    json_map = {"topics": topics_data}

    json_index_path.write_text(
        json.dumps(json_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Successfully generated metadata-rich index at {json_index_path}")


if __name__ == "__main__":
    refresh_index()
