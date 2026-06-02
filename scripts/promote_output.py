"""Promote a query output back into wiki (dry-run by default)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from config import OUTPUTS_DIR, WORKSPACE_PATH
from models import WikiPage
from wiki_themes import load_existing_themes

logger = logging.getLogger(__name__)


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def _extract_answer_body(text: str) -> str:
    body = _strip_frontmatter(text)
    m = re.search(r"## Conversation\s*\n(.*)", body, re.DOTALL | re.IGNORECASE)
    if m:
        convo = m.group(1).strip()
        m2 = re.search(
            r"\*\*Assistant\*\*:\s*(.*)",
            convo,
            re.DOTALL | re.IGNORECASE,
        )
        if m2:
            return m2.group(1).strip()
    if "## Analysis" in body or "## Answer" in body:
        return body
    return body


def resolve_output_path(file_arg: str) -> Path:
    path = Path(file_arg)
    if not path.is_absolute():
        path = WORKSPACE_PATH / path
    if not path.exists():
        path = OUTPUTS_DIR / file_arg
    if not path.exists():
        raise FileNotFoundError(f"Output not found: {file_arg}")
    return path


def resolve_target_page(target_title: str) -> WikiPage:
    _, title_to_path = load_existing_themes()
    if target_title not in title_to_path:
        raise ValueError(
            f"Wiki page not found for title: {target_title!r}. "
            "Use exact title from INDEX.json / wiki filename stem."
        )
    return WikiPage(title_to_path[target_title])


def promote_output(
    output_file: str,
    target_title: str,
    *,
    confirm: bool = False,
) -> dict:
    """Merge query output into target wiki page. Returns summary dict."""
    out_path = resolve_output_path(output_file)
    page = resolve_target_page(target_title)
    rel_output = str(out_path.relative_to(WORKSPACE_PATH))
    body = _extract_answer_body(out_path.read_text(encoding="utf-8"))
    if not body.strip():
        raise ValueError(f"No promotable content in {out_path}")

    stamp = datetime.now().strftime("%Y-%m-%d")
    distillation = (
        f"\n\n### Promoted from query ({stamp}) — source: [[{rel_output}]]\n"
        f"{body.strip()}\n"
    )

    summary = {
        "output": rel_output,
        "target": str(page.file_path.relative_to(WORKSPACE_PATH)),
        "target_title": target_title,
        "bytes": len(body),
        "confirm": confirm,
    }

    if not confirm:
        logger.info("DRY RUN — pass --confirm to apply")
        summary["preview"] = distillation[:500] + ("…" if len(distillation) > 500 else "")
        return summary

    if distillation.strip() not in page.body:
        page.body += distillation

    if rel_output not in page.sources:
        page.sources.append(rel_output)

    tags = set(page.front_matter.get("tags", []) or [])
    tags.add("type/shift")
    page.front_matter["tags"] = list(tags)

    evo = (
        f"- {stamp}: Promoted query output [[{rel_output}]] into this page "
        f"(type/shift)."
    )
    if evo not in page.evolution:
        page.evolution = (page.evolution + "\n" + evo).strip()

    page.save()
    logger.info("Promoted %s → %s", rel_output, page.file_path.name)
    summary["applied"] = True
    return summary
