"""Load wiki theme index for ingest prepare/apply (deterministic)."""

from __future__ import annotations

import re
from pathlib import Path

from config import WIKI_DIR, WORKSPACE_PATH


def _strip_yaml_value(raw: str) -> str:
    return raw.strip().strip("'\"")


def load_existing_themes() -> tuple[list[dict], dict[str, Path]]:
    """Return theme records and title/alias -> wiki file path."""
    themes: list[dict] = []
    title_to_path: dict[str, Path] = {}
    seen: set[str] = set()

    for f in WIKI_DIR.rglob("*.md", recurse_symlinks=True):
        if f.name in {"INDEX.md", "audit.md"}:
            continue
        try:
            content = f.read_text(encoding="utf-8")
            title = f.stem
            alias = ""

            t_match = re.search(r"^title:\s*(.*)", content, re.MULTILINE)
            if t_match:
                title = _strip_yaml_value(t_match.group(1))
            a_match = re.search(r"^alias:\s*(.*)", content, re.MULTILINE)
            if a_match:
                alias = _strip_yaml_value(a_match.group(1))

            rel = str(f.relative_to(WORKSPACE_PATH))
            key = f"{title}|{rel}"
            if key not in seen:
                themes.append({"title": title, "path": rel, "alias": alias or None})
                seen.add(key)

            title_to_path[title] = f
            if alias:
                title_to_path[alias] = f
        except OSError:
            continue

    themes.sort(key=lambda t: t["title"].lower())
    return themes, title_to_path
