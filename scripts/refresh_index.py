"""Refresh INDEX.json and log/index.md (deterministic)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from config import INDEX_MD, LOG_DIR, WIKI_DIR, WORKSPACE_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_yaml_field(content: str, field: str):
    match = re.search(rf"^{field}:\s*(.*)", content, re.MULTILINE)
    if not match:
        return None

    block_match = re.search(
        rf"^{field}:\s*(?:.*(?:\n\s*[-*].*)*)", content, re.MULTILINE | re.DOTALL
    )
    if block_match:
        block = block_match.group(0)
        tags = re.findall(rf"^\s*[-*]\s*(.*)", block, re.MULTILINE)
        if tags:
            return [t.strip().strip("'\" ") for t in tags if t.strip()]

    val = match.group(1).strip()
    if val.startswith("["):
        cleaned = val.strip("[]'\" ")
        return [t.strip().strip("'\" ") for t in cleaned.split(",") if t.strip()]
    return [val.strip("\"' ")]


def _summary_from_page(content: str) -> str:
    fm_end = re.search(r"^---\n.*?\n---\n", content, re.DOTALL)
    body = content[fm_end.end() :] if fm_end else content
    m = re.search(r"^>\s*(.+)", body, re.MULTILINE)
    if m:
        text = m.group(1).strip()
        return text[:120] + ("…" if len(text) > 120 else "")
    return ""


def refresh_index() -> None:
    json_index_path = LOG_DIR / "INDEX.json"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    topics_data: dict = {}
    index_lines = ["# Wiki Index (auto-generated)", "", "See also: [[../INDEX.md]] (Obsidian hubs)", ""]

    by_level: dict[int, list[tuple[str, str, str]]] = {0: [], 1: [], 2: []}

    for f in WIKI_DIR.rglob("*.md", recurse_symlinks=True):
        if f.name in {"INDEX.md", "audit.md"}:
            continue

        try:
            content = f.read_text(encoding="utf-8")
            fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            fm_content = fm_match.group(1) if fm_match else content

            level_val = get_yaml_field(fm_content, "level")
            try:
                level = (
                    int(level_val[0])
                    if isinstance(level_val, list)
                    else int(level_val or 0)
                )
            except (TypeError, ValueError):
                level = 0

            tags = get_yaml_field(fm_content, "tags") or []
            alias_val = get_yaml_field(fm_content, "alias")
            alias = (
                alias_val[0]
                if isinstance(alias_val, list) and alias_val
                else (alias_val or "")
            )

            title_val = get_yaml_field(fm_content, "title")
            title = (
                title_val[0]
                if isinstance(title_val, list) and title_val
                else (title_val or f.stem)
            )

            rel = str(f.relative_to(WORKSPACE_PATH))
            summary = _summary_from_page(content)

            topics_data[f.stem] = {
                "path": rel,
                "level": level,
                "tags": tags,
                "alias": alias,
                "title": title,
            }

            by_level.setdefault(level, []).append((title, rel, summary))
        except OSError as exc:
            logger.warning("Failed to index %s: %s", f.name, exc)

    json_index_path.write_text(
        json.dumps({"topics": topics_data}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Generated %s", json_index_path.relative_to(WORKSPACE_PATH))

    for level in sorted(by_level.keys()):
        label = {0: "Level 0 / Other", 1: "Level 1 / Synthesis", 2: "Level 2 / Principle"}.get(
            level, f"Level {level}"
        )
        index_lines.append(f"## {label}")
        index_lines.append("")
        for title, rel, summary in sorted(by_level[level], key=lambda x: x[0].lower()):
            line = f"- [[{rel}|{title}]]"
            if summary:
                line += f" — {summary}"
            index_lines.append(line)
        index_lines.append("")

    INDEX_MD.write_text("\n".join(index_lines).strip() + "\n", encoding="utf-8")
    logger.info("Generated %s", INDEX_MD.relative_to(WORKSPACE_PATH))


if __name__ == "__main__":
    refresh_index()
