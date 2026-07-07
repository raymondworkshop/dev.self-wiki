"""Build lunr-ready search index."""

from __future__ import annotations

import json
from typing import Any

from memex.cache import MEMEX_DIR
from memex.queries import get_backlinks, get_outgoing
from memex.resolve import normalize_url
from memex.search_expand import expand_for_search
from memex.sources import VaultPage, get_excerpt, get_topics, is_vault_index, strip_backlinks_block, strip_markdown

BODY_INDEX_MAX = 8000


def _layer_label(page: VaultPage) -> str:
    return page.layer.replace("_", " ").title() if page.layer else "Vault"


def collect_search_entries(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    layer_hubs = ctx.get("layer_hubs", {})
    pages_by_rel = ctx.get("pages_by_rel", {})

    for idx, page in enumerate(pages_by_rel.values(), start=1):
        if is_vault_index(page):
            continue
        hub = layer_hubs.get(page.layer, {})
        topics = get_topics(page)
        excerpt = get_excerpt(page)
        body_plain = strip_markdown(strip_backlinks_block(page.body))[:BODY_INDEX_MAX]
        entries.append(
            {
                "id": str(idx),
                "title": page.title,
                "title_search": expand_for_search(page.title),
                "url": page.url,
                "layer": _layer_label(page),
                "hub_url": hub.get("url", ""),
                "hub_title": hub.get("title", ""),
                "topics": topics,
                "topics_search": expand_for_search(" ".join(topics)),
                "excerpt": excerpt,
                "excerpt_search": expand_for_search(excerpt),
                "body": body_plain,
                "body_search": expand_for_search(body_plain),
                "backlink_count": len(get_backlinks(page, ctx)),
                "outgoing_count": len(get_outgoing(page, ctx)),
                "rel": page.rel,
            }
        )
    return sorted(entries, key=lambda x: x["title"].lower())


def write_search_index(ctx: dict[str, Any]) -> None:
    MEMEX_DIR.mkdir(parents=True, exist_ok=True)
    entries = collect_search_entries(ctx)
    path = MEMEX_DIR / "search-index.json"
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
