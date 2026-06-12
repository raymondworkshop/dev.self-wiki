import logging
import re

from config import WORKSPACE_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def update_backlinks():
    self_wiki_dir = WORKSPACE_PATH / "self-wiki"
    wiki_dir = self_wiki_dir / "wiki"
    wiki_files = [
        f
        for f in wiki_dir.rglob("*.md", recurse_symlinks=True)
        if f.name not in ["INDEX.md", "audit.md"] and not f.name.endswith("-Hub.md")
    ]

    # Map filenames, titles, and aliases to their file stems
    topic_map = {}
    for f in wiki_files:
        stem = f.stem
        topic_map[stem] = stem

        # Parse YAML front matter for title and alias
        content = f.read_text(encoding="utf-8")
        title_match = re.search(r"^title:\s*(.*)$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip().strip("'").strip('"')
            if title:
                topic_map[title] = stem

        alias_match = re.search(r"^alias:\s*(.*)$", content, re.MULTILINE)
        if alias_match:
            alias = alias_match.group(1).strip().strip("'").strip('"')
            if alias:
                topic_map[alias] = stem

    # file_data = { file_stem -> { rel_type -> set(topics) } }
    file_data = {
        f.stem: {"Evolved from": set(), "Contradicts": set(), "Mentioned in": set()}
        for f in wiki_files
    }

    # Keywords for contradiction
    CONTRADICT_KEYWORDS = ["contradict", "矛盾", "冲突", "反驳", "不同于"]
    # Regex for evolution section
    EVOLUTION_PATTERN = re.compile(
        r"## (?:Evolution|演进|演化)(.*?)(?=\n##|\Z)", re.IGNORECASE | re.DOTALL
    )

    # 1. Scan files to build relationship map
    for f in wiki_files:
        content = f.read_text(encoding="utf-8")
        stem = f.stem

        # Strip Backlinks section before scanning to avoid recursive mentions
        scan_content = re.sub(
            r"## Backlinks\n<!-- BEGIN BACKLINKS -->.*?<!-- END BACKLINKS -->",
            "",
            content,
            flags=re.DOTALL,
        )
        lines = scan_content.splitlines()

        evolution_match = EVOLUTION_PATTERN.search(scan_content)
        evolution_text = evolution_match.group(1) if evolution_match else ""

        # Find all [[links]] in scan_content
        links = re.findall(r"\[\[(.*?)\]\]", scan_content)
        for link_text in links:
            # Check if link_text matches a known stem, title, or alias
            target_stem = topic_map.get(link_text)

            if target_stem and target_stem != stem:
                link = f"[[{target_stem}]]"  # Use canonical stem for storage

                # Add "Mentioned in" to the target (traditional backlink)
                file_data[target_stem]["Mentioned in"].add(f"[[{stem}]]")

                # Check if it's an "Evolved from" relationship for the current file
                if f"[[{link_text}]]" in evolution_text:
                    file_data[stem]["Evolved from"].add(link)

                # Check if it's a "Contradicts" relationship for the current file
                for line in lines:
                    if f"[[{link_text}]]" in line and any(
                        kw in line.lower() for kw in CONTRADICT_KEYWORDS
                    ):
                        file_data[stem]["Contradicts"].add(link)
                        break

    # 2. Update files with Backlinks section
    for f in wiki_files:
        content = f.read_text(encoding="utf-8")
        stem = f.stem

        backlink_lines = []
        # Ordered as per AGENTS.md
        for rel_type in ["Evolved from", "Mentioned in", "Contradicts"]:
            topics = file_data[stem][rel_type]
            if topics:
                # Format: - **Rel type**: [[Topic A]], [[Topic B]]
                backlink_lines.append(f"- **{rel_type}**: {', '.join(sorted(topics))}")

        # Remove old section if it exists
        new_content = re.sub(
            r"\n?## Backlinks\n<!-- BEGIN BACKLINKS -->.*?<!-- END BACKLINKS -->\n?",
            "",
            content,
            flags=re.DOTALL,
        )

        if backlink_lines:
            backlink_section = "\n## Backlinks\n<!-- BEGIN BACKLINKS -->\n"
            backlink_section += "\n".join(backlink_lines) + "\n"
            backlink_section += "<!-- END BACKLINKS -->\n"

            # Find insertion point: before ## Sources (case insensitive)
            sources_match = re.search(
                r"^##\s+sources", new_content, re.IGNORECASE | re.MULTILINE
            )
            if sources_match:
                idx = sources_match.start()
                new_content = (
                    new_content[:idx] + backlink_section + "\n" + new_content[idx:]
                )
            else:
                new_content = new_content.rstrip() + "\n" + backlink_section

        if new_content.strip() != content.strip():
            f.write_text(new_content, encoding="utf-8")
            logger.info(f"Updated backlinks for: {f.name}")
        else:
            logger.debug(f"No changes for: {f.name}")


if __name__ == "__main__":
    update_backlinks()
