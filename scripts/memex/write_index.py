"""Write memex browse index (wiki themes, backlinks, layer hubs)."""

from __future__ import annotations

import html
from typing import Any

from memex.cache import MEMEX_DIR
from memex.config import VAULT_LAYERS
from memex.queries import (
    get_layer_hub_summaries,
    get_layer_top_pages,
    get_top_referenced_pages,
    get_wiki_ranked,
)
from site_theme import render_page, search_panel_html


def _wiki_card(
    title: str,
    url: str,
    *,
    excerpt: str = "",
    backlink_count: int = 0,
    layer: str = "",
) -> str:
    meta_parts = []
    if layer:
        meta_parts.append(html.escape(layer))
    if backlink_count:
        label = "backlink" if backlink_count == 1 else "backlinks"
        meta_parts.append(f"{backlink_count} {label}")
    meta = " · ".join(meta_parts)
    excerpt_html = (
        f'<p class="wiki-card-excerpt">{html.escape(excerpt)}</p>' if excerpt else ""
    )
    meta_html = f'<p class="wiki-mentions">{meta}</p>' if meta else ""
    return (
        f'<li class="wiki-card">'
        f'<h3><a href="{html.escape(url)}">{html.escape(title)}</a></h3>'
        f"{excerpt_html}{meta_html}"
        f"</li>"
    )


def _wiki_panel(title: str, note: str, cards: list[str]) -> str:
    if not cards:
        return ""
    return (
        f'<section class="wiki-panel">'
        f"<h2>{html.escape(title)}</h2>"
        f'<p class="wiki-panel-note">{html.escape(note)}</p>'
        f'<ul class="wiki-card-list">{"".join(cards)}</ul>'
        f"</section>"
    )


def _stats_panel(stats: dict[str, Any], wiki_count: int) -> str:
    if not stats:
        return ""
    rows = [
        ("pages", stats.get("pages", 0)),
        ("wiki themes", wiki_count),
        ("wikilinks", stats.get("wikilinks", 0)),
        ("internal links", stats.get("internal_links", 0)),
        ("lines", stats.get("lines", 0)),
    ]
    items = "".join(f"<li>{html.escape(str(label))} = {value}</li>" for label, value in rows)
    return (
        '<section class="wiki-panel memex-stats">'
        "<h2>Stats</h2>"
        f'<ul class="memex-stats-list">{items}</ul>'
        "</section>"
    )


def write_memex_index(ctx: dict[str, Any]) -> None:
    MEMEX_DIR.mkdir(parents=True, exist_ok=True)
    stats = ctx.get("stats", {})

    wiki_ranked = get_wiki_ranked(ctx)
    top_referenced = get_top_referenced_pages(ctx, limit=12)
    hub_summaries = get_layer_hub_summaries(ctx)

    hub_cards = [
        _wiki_card(
            hub["title"],
            hub["url"],
            excerpt=hub.get("excerpt", ""),
            backlink_count=hub.get("backlink_count", 0),
            layer=f'{hub["layer"]}/',
        )
        for hub in hub_summaries
    ]

    wiki_cards = [
        _wiki_card(
            page["title"],
            page["url"],
            excerpt=page.get("excerpt", ""),
            backlink_count=page.get("backlink_count", 0),
            layer="wiki",
        )
        for page in wiki_ranked
    ]

    top_cards = [
        _wiki_card(
            page["title"],
            page["url"],
            backlink_count=page.get("backlink_count", 0),
            layer=page.get("layer", ""),
        )
        for page in top_referenced
    ]

    layer_sections: list[str] = []
    for layer in VAULT_LAYERS:
        if layer == "wiki":
            continue
        top_pages = get_layer_top_pages(ctx, layer, limit=8)
        if not top_pages:
            continue
        layer_cards = [
            _wiki_card(
                page["title"],
                page["url"],
                backlink_count=page.get("backlink_count", 0),
                layer=layer,
            )
            for page in top_pages
        ]
        hub_url = ctx.get("layer_hubs", {}).get(layer, {}).get("url", f"/{layer}/index.html")
        layer_sections.append(
            _wiki_panel(
                f"{layer.replace('_', ' ').title()} — most linked",
                f"Top pages in {layer}/. Browse all via the layer index.",
                layer_cards,
            )
            + f'<p class="wiki-panel-note"><a href="{html.escape(hub_url)}">'
            f"Open {html.escape(layer)}/ index →</a></p>"
        )

    body = (
        search_panel_html()
        + '<div class="memex-intro"><h2>Explore the vault</h2>'
        + "<p class=\"wiki-panel-note\">Wiki themes, backlinks, and layer hubs across your second brain.</p></div>"
        + _wiki_panel(
            "Areas",
            "Each layer is a hub — a map into a corner of this vault.",
            hub_cards,
        )
        + _wiki_panel(
            "Wiki themes",
            "Synthesized belief pages in wiki/, sorted by how often other notes link here.",
            wiki_cards,
        )
        + _wiki_panel(
            "Most linked across vault",
            "Pages that other notes link to most often (excluding layer hubs).",
            top_cards,
        )
        + "".join(layer_sections)
        + _stats_panel(stats, len(wiki_ranked))
    )

    page_html = render_page(
        "Memex",
        body,
        rel_path="memex/index.html",
        hero_title="Memex",
        subtitle="Wiki themes, backlinks, and layer hubs",
        compact=False,
        with_search=True,
    )
    (MEMEX_DIR / "index.html").write_text(page_html, encoding="utf-8")
