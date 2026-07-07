"""Render memex link panels for published HTML."""

from __future__ import annotations

import html
from typing import Any

from memex.backliner import TYPED_RELATIONS
from memex.queries import get_backlinks, get_outgoing, get_typed_backlinks, get_unlinked_mentions
from memex.sources import VaultPage


def _link_list(items: list[dict[str, str]], *, limit: int = 30) -> str:
    if not items:
        return ""
    parts = []
    for item in items[:limit]:
        parts.append(
            f'<a href="{html.escape(item["url"])}">{html.escape(item["title"])}</a>'
        )
    if len(items) > limit:
        parts.append(f"<span>…and {len(items) - limit} more</span>")
    return ", ".join(parts)


def render_panels(page: VaultPage, ctx: dict[str, Any]) -> str:
    outgoing = get_outgoing(page, ctx)
    backlinks = get_backlinks(page, ctx)
    unlinked = get_unlinked_mentions(page, ctx)
    typed = get_typed_backlinks(page, ctx)

    sections: list[str] = []

    if outgoing:
        sections.append(
            f'<section class="memex-panel"><h3>Links to ({len(outgoing)})</h3>'
            f"<p>{_link_list(outgoing)}</p></section>"
        )

    if page.layer == "wiki":
        for rel_type in TYPED_RELATIONS:
            refs = typed.get(rel_type, [])
            if refs:
                sections.append(
                    f'<section class="memex-panel"><h3>{html.escape(rel_type)} ({len(refs)})</h3>'
                    f"<p>{_link_list(refs)}</p></section>"
                )

    if backlinks:
        sections.append(
            f'<section class="memex-panel"><h3>Linked from ({len(backlinks)})</h3>'
            f"<p>{_link_list(backlinks)}</p></section>"
        )

    if unlinked:
        sections.append(
            f'<section class="memex-panel"><h3>Unlinked mentions ({len(unlinked)})</h3>'
            f"<p>{_link_list(unlinked)}</p></section>"
        )

    if not sections:
        return ""
    return '<div class="memex-panels">' + "\n".join(sections) + "</div>"
