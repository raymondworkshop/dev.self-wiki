"""Export typed ## Backlinks to wiki/*.md for Obsidian."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from config import WIKI_DIR
from memex.backliner import TYPED_RELATIONS
from memex.resolve import normalize_url

logger = logging.getLogger(__name__)

SKIP_FILES = {"INDEX.md", "audit.md"}


def _format_wikilink(ref: dict[str, str]) -> str:
    rel = ref.get("rel", "")
    if rel:
        stem = Path(rel).stem
    else:
        stem = Path(ref["url"]).stem
    return f"[[{stem}]]"


def export_wiki_backlinks(ctx: dict[str, Any] | None = None) -> int:
    if ctx is None:
        from memex.graph import build_memex_context

        ctx = build_memex_context()

    typed = ctx.get("typed_backlinks", {})
    pages_by_rel = ctx.get("pages_by_rel", {})
    updated = 0

    for path in WIKI_DIR.rglob("*.md", recurse_symlinks=True):
        if path.name in SKIP_FILES or path.name.endswith("-Hub.md"):
            continue

        vault_rel = f"wiki/{path.relative_to(WIKI_DIR).as_posix()}"
        page = pages_by_rel.get(vault_rel)
        if not page:
            continue

        page_url = normalize_url(page.url)
        page_typed = typed.get(page_url, {})

        backlink_lines: list[str] = []
        for rel_type in TYPED_RELATIONS:
            refs = page_typed.get(rel_type, [])
            if refs:
                links = ", ".join(sorted(_format_wikilink(r) for r in refs))
                backlink_lines.append(f"- **{rel_type}**: {links}")

        content = path.read_text(encoding="utf-8")
        new_content = re.sub(
            r"\n?## Backlinks\n<!-- BEGIN BACKLINKS -->.*?<!-- END BACKLINKS -->\n?",
            "",
            content,
            flags=re.DOTALL,
        )

        backlink_section = "\n## Backlinks\n<!-- BEGIN BACKLINKS -->\n"
        if backlink_lines:
            backlink_section += "\n".join(backlink_lines) + "\n"
        backlink_section += "<!-- END BACKLINKS -->\n"

        sources_match = re.search(r"^##\s+sources", new_content, re.IGNORECASE | re.MULTILINE)
        if sources_match:
            idx = sources_match.start()
            new_content = new_content[:idx] + backlink_section + "\n" + new_content[idx:]
        else:
            new_content = new_content.rstrip() + "\n" + backlink_section

        if new_content.strip() != content.strip():
            path.write_text(new_content, encoding="utf-8")
            logger.info("Updated backlinks for: %s", path.name)
            updated += 1

    return updated
