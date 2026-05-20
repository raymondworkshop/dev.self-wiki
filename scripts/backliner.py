import logging
import os
import re
from pathlib import Path

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


def update_backlinks():
    self_wiki_dir = WORKSPACE_PATH / "self-wiki"
    wiki_dir = self_wiki_dir / "wiki"
    wiki_files = [
        f
        for f in wiki_dir.rglob("*.md")
        if f.name not in ["INDEX.md", "audit.md"] and not f.name.endswith("-Hub.md")
    ]

    # Map topics to their file paths
    topic_map = {f.stem: f"[[{f.stem}]]" for f in wiki_files}
    backlinks = {
        f.stem: {"Evolved from": set(), "Mentioned in": set(), "Contradicts": set()}
        for f in wiki_files
    }

    # 1. Scan files to build backlink map
    for f in wiki_files:
        content = f.read_text(encoding="utf-8")

        # Detect relationships based on section headers or keywords
        # This is a heuristic that can be refined
        evolution_section = re.search(
            r"## Evolution(.*?)(?=\n##|\Z)", content, re.DOTALL
        )

        for topic, link in topic_map.items():
            if topic == f.stem:
                continue

            if link in content:
                if evolution_section and link in evolution_section.group(1):
                    backlinks[topic]["Evolved from"].add(f"[[{f.stem}]]")
                elif "contradict" in content.lower() and link in content:
                    backlinks[topic]["Contradicts"].add(f"[[{f.stem}]]")
                else:
                    backlinks[topic]["Mentioned in"].add(f"[[{f.stem}]]")

    # 2. Update files with Backlinks section
    for f in wiki_files:
        content = f.read_text(encoding="utf-8")

        backlink_section = "\n## Backlinks\n<!-- BEGIN BACKLINKS -->\n"

        for rel_type, topics in backlinks[f.stem].items():
            if topics:
                backlink_section += f"- **{rel_type}**: {', '.join(sorted(topics))}\n"

        backlink_section += "<!-- END BACKLINKS -->\n"

        # Remove old section if exists
        new_content = re.sub(
            r"## Backlinks\n<!-- BEGIN BACKLINKS -->.*?<!-- END BACKLINKS -->\n",
            "",
            content,
            flags=re.DOTALL,
        )

        # Append new section before sources
        if "## sources" in new_content.lower():
            new_content = new_content.replace(
                "## sources", f"{backlink_section}\n## sources"
            )
        else:
            new_content += f"\n{backlink_section}"

        f.write_text(new_content, encoding="utf-8")
        logger.info(f"Updated backlinks for: {f.name}")


if __name__ == "__main__":
    update_backlinks()
