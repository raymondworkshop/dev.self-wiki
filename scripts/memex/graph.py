"""Build full-vault memex link graph."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Any

from memex.backliner import build_typed_edges
from memex.config import (
    HASHTAG_TAG_LINE,
    HASHTAG_TOKEN,
    MARKDOWN_LINK_PATTERN,
    VAULT_LAYERS,
    WIKILINK_PATTERN,
)
from memex.links import build_unlinked_mentions, iter_resolved_links
from memex.resolve import (
    build_fuzzy_lookup,
    build_url_registry,
    normalize_url,
    register_target,
    resolve_target,
)
from memex.sources import (
    VaultPage,
    collect_vault_pages,
    get_aliases,
    get_excerpt,
    get_topics,
    is_vault_index,
    layer_hub_url,
    strip_backlinks_block,
    strip_markdown,
)


def _layer_display(layer: str) -> str:
    return layer.replace("_", " ").title() if layer else "Vault"


def build_memex_context() -> dict[str, Any]:
    pages = collect_vault_pages()
    registry: dict[str, dict[str, str]] = {}
    layer_hubs: dict[str, dict[str, str]] = {}
    layer_pages: dict[str, list[dict[str, str]]] = defaultdict(list)

    for layer in VAULT_LAYERS:
        layer_hubs[layer] = {
            "title": _layer_display(layer),
            "url": layer_hub_url(layer),
            "rel": f"{layer}/index.md",
        }
        register_target(
            registry,
            _layer_display(layer),
            layer_hub_url(layer),
            rel=f"{layer}/",
        )

    page_count = 0
    for page in pages:
        if is_vault_index(page):
            register_target(registry, page.title, page.url, rel=page.rel)
            continue
        page_count += 1
        register_target(
            registry,
            page.title,
            page.url,
            stem=page.stem,
            aliases=get_aliases(page),
            rel=page.rel,
        )
        layer_pages[page.layer].append(
            {
                "title": page.title,
                "url": page.url,
                "rel": page.rel,
                "excerpt": get_excerpt(page),
            }
        )

    for layer in layer_pages:
        layer_pages[layer] = sorted(layer_pages[layer], key=lambda x: x["title"].lower())

    url_registry = build_url_registry(registry)
    fuzzy_lookup = build_fuzzy_lookup(pages)

    topic_pages: dict[str, list[dict[str, str]]] = defaultdict(list)
    page_topics: dict[str, list[str]] = {}
    for page in pages:
        if is_vault_index(page):
            continue
        page_url = normalize_url(page.url)
        topics = get_topics(page)
        page_topics[page_url] = topics
        entry = {"title": page.title, "url": page.url, "layer": page.layer}
        for topic in topics:
            topic_pages[topic].append(entry)
    for topic in topic_pages:
        topic_pages[topic] = sorted(topic_pages[topic], key=lambda x: x["title"].lower())

    backlinks: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_backlinks: set[tuple[str, str]] = set()
    outgoing_urls: dict[str, set[str]] = defaultdict(set)
    plain_bodies: dict[str, str] = {}
    wikilink_count = 0
    line_count = 0

    for page in pages:
        body = strip_backlinks_block(page.body)
        line_count += body.count("\n") + (1 if body else 0)
        wikilink_count += len(WIKILINK_PATTERN.findall(body))
        source_url = normalize_url(page.url)
        plain_bodies[source_url] = strip_markdown(body)

        for entry in iter_resolved_links(
            page.body,
            registry,
            url_registry,
            page=page,
            layer_hubs=layer_hubs,
            fuzzy_lookup=fuzzy_lookup,
        ):
            target_url = normalize_url(entry["url"])
            if target_url == source_url:
                continue
            outgoing_urls[source_url].add(target_url)
            key = (target_url, source_url)
            if key in seen_backlinks:
                continue
            seen_backlinks.add(key)
            edge = {
                "title": page.title,
                "url": page.url,
                "rel": page.rel,
                "layer": page.layer,
            }
            if entry.get("edge_type"):
                edge["edge_type"] = entry["edge_type"]
            backlinks[target_url].append(edge)

    for url in backlinks:
        backlinks[url] = sorted(backlinks[url], key=lambda x: x["title"].lower())

    wiki_pages = [p for p in pages if p.layer == "wiki"]
    typed_backlinks = build_typed_edges(wiki_pages, registry, fuzzy_lookup=fuzzy_lookup)

    backlink_counts = {normalize_url(u): len(items) for u, items in backlinks.items()}
    unlinked_mentions = build_unlinked_mentions(
        [p for p in pages if not is_vault_index(p)],
        fuzzy_lookup,
        outgoing_urls,
        plain_bodies,
    )

    hashtag_link_count = 0
    internal_link_count = 0
    for page in pages:
        body = strip_backlinks_block(page.body)
        for line in body.splitlines():
            stripped = line.strip()
            if HASHTAG_TAG_LINE.match(stripped):
                for match in HASHTAG_TOKEN.finditer(stripped):
                    if resolve_target(match.group(0)[1:], registry, fuzzy_lookup=fuzzy_lookup):
                        hashtag_link_count += 1
        internal_link_count += len(
            [
                m
                for m in MARKDOWN_LINK_PATTERN.finditer(body)
                if url_registry.get(normalize_url(m.group(2)))
                or resolve_target(m.group(1).strip(), registry, fuzzy_lookup=fuzzy_lookup)
            ]
        )

    stats = {
        "date": date.today().isoformat(),
        "files": len(pages),
        "pages": page_count,
        "wikilinks": wikilink_count,
        "hashtag_links": hashtag_link_count,
        "internal_links": internal_link_count,
        "lines": line_count,
    }

    return {
        "registry": registry,
        "url_registry": url_registry,
        "fuzzy_lookup": fuzzy_lookup,
        "title_lookup": fuzzy_lookup,
        "backlink_counts": backlink_counts,
        "unlinked_mentions": unlinked_mentions,
        "topic_pages": dict(topic_pages),
        "page_topics": page_topics,
        "backlinks": dict(backlinks),
        "typed_backlinks": typed_backlinks,
        "layer_pages": dict(layer_pages),
        "layer_hubs": layer_hubs,
        "pages_by_rel": {p.rel: p for p in pages},
        "pages_by_url": {normalize_url(p.url): p for p in pages},
        "stats": stats,
    }
