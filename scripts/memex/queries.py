"""Memex query helpers."""

from __future__ import annotations

from typing import Any

from memex.links import iter_resolved_links
from memex.resolve import normalize_url
from memex.sources import VaultPage, get_topics, strip_backlinks_block


def get_backlinks(page: VaultPage, ctx: dict[str, Any]) -> list[dict[str, str]]:
    return ctx.get("backlinks", {}).get(normalize_url(page.url), [])


def get_typed_backlinks(page: VaultPage, ctx: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    return ctx.get("typed_backlinks", {}).get(normalize_url(page.url), {})


def get_outgoing(page: VaultPage, ctx: dict[str, Any]) -> list[dict[str, str]]:
    registry = ctx.get("registry", {})
    url_registry = ctx.get("url_registry", {})
    layer_hubs = ctx.get("layer_hubs", {})
    fuzzy_lookup = ctx.get("fuzzy_lookup", [])
    source_url = normalize_url(page.url)
    links = [
        {"title": e["title"], "url": e["url"], "rel": e.get("rel", "")}
        for e in iter_resolved_links(
            page.body,
            registry,
            url_registry,
            page=page,
            layer_hubs=layer_hubs,
            fuzzy_lookup=fuzzy_lookup,
        )
        if normalize_url(e["url"]) != source_url
    ]
    return sorted(links, key=lambda x: x["title"].lower())


def get_unlinked_mentions(page: VaultPage, ctx: dict[str, Any]) -> list[dict[str, str]]:
    return ctx.get("unlinked_mentions", {}).get(normalize_url(page.url), [])


def find_missing_links(ctx: dict[str, Any]) -> list[dict[str, str]]:
    from memex.config import WIKILINK_PATTERN
    from memex.resolve import resolve_target

    registry = ctx.get("registry", {})
    fuzzy_lookup = ctx.get("fuzzy_lookup", [])
    missing: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for page in ctx.get("pages_by_rel", {}).values():
        body = strip_backlinks_block(page.body)
        for match in WIKILINK_PATTERN.finditer(body):
            raw = match.group(1).strip()
            if resolve_target(raw, registry, fuzzy_lookup=fuzzy_lookup):
                continue
            key = (page.rel, raw)
            if key in seen:
                continue
            seen.add(key)
            missing.append({"source": page.rel, "target": raw, "title": page.title})
    return sorted(missing, key=lambda x: (x["source"], x["target"]))


def get_orphans(ctx: dict[str, Any]) -> list[dict[str, str]]:
    backlinks = ctx.get("backlinks", {})
    orphans: list[dict[str, str]] = []
    for page in ctx.get("pages_by_rel", {}).values():
        if page.rel == "INDEX.md":
            continue
        if not backlinks.get(normalize_url(page.url)):
            orphans.append({"title": page.title, "url": page.url, "rel": page.rel})
    return sorted(orphans, key=lambda x: x["title"].lower())


def _layer_hub_urls(ctx: dict[str, Any]) -> set[str]:
    return {normalize_url(hub["url"]) for hub in ctx.get("layer_hubs", {}).values()}


def get_top_linked(
    ctx: dict[str, Any],
    n: int = 15,
    *,
    layer: str | None = None,
    exclude_hubs: bool = True,
) -> list[dict[str, Any]]:
    counts = ctx.get("backlink_counts", {})
    pages = ctx.get("pages_by_url", {})
    hub_urls = _layer_hub_urls(ctx) if exclude_hubs else set()
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    result: list[dict[str, Any]] = []
    for url, count in ranked:
        if exclude_hubs and url in hub_urls:
            continue
        page = pages.get(url)
        if not page:
            continue
        if layer and page.layer != layer:
            continue
        result.append(
            {
                "title": page.title,
                "url": page.url,
                "rel": page.rel,
                "layer": page.layer,
                "count": count,
                "backlink_count": count,
            }
        )
        if len(result) >= n:
            break
    return result


def get_top_referenced_pages(ctx: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    return get_top_linked(ctx, limit, exclude_hubs=True)


def get_wiki_ranked(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    counts = ctx.get("backlink_counts", {})
    wiki_pages = ctx.get("layer_pages", {}).get("wiki", [])
    ranked: list[dict[str, Any]] = []
    for page in wiki_pages:
        rel = page.get("rel", "")
        if rel.endswith("/index.md") or rel.endswith("/INDEX.md"):
            continue
        url = normalize_url(page["url"])
        ranked.append(
            {
                "title": page["title"],
                "url": page["url"],
                "rel": rel,
                "layer": "wiki",
                "excerpt": page.get("excerpt", ""),
                "backlink_count": counts.get(url, 0),
            }
        )
    ranked.sort(key=lambda x: (-x["backlink_count"], x["title"].lower()))
    return ranked


def get_layer_hub_summaries(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    from memex.config import VAULT_LAYERS
    from memex.sources import get_excerpt

    counts = ctx.get("backlink_counts", {})
    layer_hubs = ctx.get("layer_hubs", {})
    pages_by_rel = ctx.get("pages_by_rel", {})
    summaries: list[dict[str, Any]] = []
    for layer in VAULT_LAYERS:
        hub = layer_hubs.get(layer)
        if not hub:
            continue
        index_page = pages_by_rel.get(f"{layer}/index.md") or pages_by_rel.get(
            f"{layer}/INDEX.md"
        )
        excerpt = get_excerpt(index_page) if index_page else ""
        summaries.append(
            {
                "title": hub["title"],
                "url": hub["url"],
                "layer": layer,
                "excerpt": excerpt,
                "backlink_count": counts.get(normalize_url(hub["url"]), 0),
            }
        )
    return summaries


def get_layer_top_pages(
    ctx: dict[str, Any], layer: str, limit: int = 8
) -> list[dict[str, Any]]:
    return get_top_linked(ctx, limit, layer=layer, exclude_hubs=True)


def get_contradicts(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    pages = ctx.get("pages_by_url", {})
    for target_url, typed in ctx.get("typed_backlinks", {}).items():
        for source in typed.get("Contradicts", []):
            target = pages.get(target_url)
            edges.append(
                {
                    "source_title": source["title"],
                    "source_url": source["url"],
                    "target_title": target.title if target else target_url,
                    "target_url": target.url if target else target_url,
                }
            )
    return sorted(edges, key=lambda x: (x["source_title"], x["target_title"]))


def get_related(page: VaultPage, ctx: dict[str, Any], limit: int = 8) -> list[dict[str, str]]:
    my_url = normalize_url(page.url)
    neighbor_urls: set[str] = set()
    for link in get_outgoing(page, ctx):
        neighbor_urls.add(normalize_url(link["url"]))
    for link in get_backlinks(page, ctx):
        neighbor_urls.add(normalize_url(link["url"]))
    neighbor_urls.discard(my_url)

    layer_pages = ctx.get("layer_pages", {}).get(page.layer, [])
    related = [p for p in layer_pages if normalize_url(p["url"]) in neighbor_urls]
    if len(related) >= limit:
        return related[:limit]

    seen = {normalize_url(p["url"]) for p in related} | {my_url}
    my_topics = set(get_topics(page))
    topic_pages = ctx.get("topic_pages", {})
    if my_topics:
        scores: dict[str, int] = {}
        page_lookup = {normalize_url(p["url"]): p for pages in ctx.get("layer_pages", {}).values() for p in pages}
        for topic in my_topics:
            for tp in topic_pages.get(topic, []):
                u = normalize_url(tp["url"])
                if u not in seen:
                    scores[u] = scores.get(u, 0) + 1
        for u, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0])):
            tp = page_lookup.get(u) or next(
                (x for pages in topic_pages.values() for x in pages if normalize_url(x["url"]) == u),
                None,
            )
            if tp:
                related.append(tp)
                seen.add(u)
            if len(related) >= limit:
                break
    return related[:limit]
