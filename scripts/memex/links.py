"""Link extraction and preprocessing for vault pages."""

from __future__ import annotations

import html
import re
from collections import defaultdict
from typing import Iterator

from memex.config import (
    HASHTAG_TAG_LINE,
    HASHTAG_TOKEN,
    MARKDOWN_LINK_PATTERN,
    WIKILINK_PATTERN,
)
from memex.resolve import (
    key_variants,
    normalize_key,
    normalize_url,
    resolve_target,
)
from memex.sources import VaultPage, get_topics, strip_backlinks_block, strip_markdown

PROVENANCE_PATTERN = re.compile(
    r"\(Source:\s*\[\[([^\]]+)\]\]\)", re.IGNORECASE
)


def iter_hashtag_links(
    body: str,
    registry: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
) -> Iterator[dict[str, str]]:
    seen: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or not HASHTAG_TAG_LINE.match(stripped):
            continue
        for match in HASHTAG_TOKEN.finditer(stripped):
            tag = match.group(0)[1:]
            entry = resolve_target(tag, registry, fuzzy_lookup=fuzzy_lookup)
            if entry and entry["url"] not in seen:
                seen.add(entry["url"])
                yield entry


def iter_topic_links(
    page: VaultPage,
    registry: dict[str, dict[str, str]],
    layer_hubs: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
) -> Iterator[dict[str, str]]:
    seen: set[str] = set()
    hub = layer_hubs.get(page.layer)
    if hub and hub["url"] not in seen:
        seen.add(hub["url"])
        yield hub
    for topic in get_topics(page):
        entry = resolve_target(topic, registry, fuzzy_lookup=fuzzy_lookup)
        if entry and entry["url"] not in seen:
            seen.add(entry["url"])
            yield entry


def iter_related_frontmatter(
    page: VaultPage,
    registry: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
) -> Iterator[dict[str, str]]:
    for field in ("related", "seealso", "see_also"):
        val = page.meta.get(field)
        if not val:
            continue
        values = val if isinstance(val, list) else [val]
        for value in values:
            entry = resolve_target(str(value).strip(), registry, fuzzy_lookup=fuzzy_lookup)
            if entry:
                yield entry


def iter_provenance_links(
    body: str,
    registry: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
) -> Iterator[dict[str, str]]:
    seen: set[str] = set()
    for match in PROVENANCE_PATTERN.finditer(body):
        entry = resolve_target(match.group(1).strip(), registry, fuzzy_lookup=fuzzy_lookup)
        if entry and entry["url"] not in seen:
            seen.add(entry["url"])
            yield {**entry, "edge_type": "provenance"}


def iter_resolved_links(
    body: str,
    registry: dict[str, dict[str, str]],
    url_registry: dict[str, dict[str, str]],
    *,
    page: VaultPage | None = None,
    layer_hubs: dict[str, dict[str, str]] | None = None,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
) -> Iterator[dict[str, str]]:
    seen: set[str] = set()
    scan_body = strip_backlinks_block(body)

    for match in WIKILINK_PATTERN.finditer(scan_body):
        entry = resolve_target(match.group(1).strip(), registry, fuzzy_lookup=fuzzy_lookup)
        if entry and entry["url"] not in seen:
            seen.add(entry["url"])
            yield entry

    for match in MARKDOWN_LINK_PATTERN.finditer(scan_body):
        url = normalize_url(match.group(2))
        entry = url_registry.get(url) or resolve_target(
            match.group(1).strip(), registry, fuzzy_lookup=fuzzy_lookup
        )
        if entry and entry["url"] not in seen:
            seen.add(entry["url"])
            yield entry

    for entry in iter_hashtag_links(scan_body, registry, fuzzy_lookup=fuzzy_lookup):
        if entry["url"] not in seen:
            seen.add(entry["url"])
            yield entry

    for entry in iter_provenance_links(scan_body, registry, fuzzy_lookup=fuzzy_lookup):
        if entry["url"] not in seen:
            seen.add(entry["url"])
            yield entry

    if page and layer_hubs is not None:
        for entry in iter_topic_links(page, registry, layer_hubs, fuzzy_lookup=fuzzy_lookup):
            if entry["url"] not in seen:
                seen.add(entry["url"])
                yield entry
        for entry in iter_related_frontmatter(page, registry, fuzzy_lookup=fuzzy_lookup):
            if entry["url"] not in seen:
                seen.add(entry["url"])
                yield entry


def label_mentioned_in_body(label: str, body: str) -> bool:
    from memex.config import CJK_RE

    if len(normalize_key(label)) < 4:
        return False
    body_lower = body.lower()
    body_compact = re.sub(r"\s+", "", body_lower)
    for variant in key_variants(label):
        if CJK_RE.search(variant):
            if variant in body_compact or variant in normalize_key(body):
                return True
            continue
        pattern = r"(?<!\w)" + re.escape(variant) + r"(?!\w)"
        if re.search(pattern, body_lower):
            return True
    return False


def build_unlinked_mentions(
    pages: list[VaultPage],
    fuzzy_lookup: list[tuple[str, dict[str, str]]],
    outgoing_urls: dict[str, set[str]],
    plain_bodies: dict[str, str],
) -> dict[str, list[dict[str, str]]]:
    labels_by_url: dict[str, tuple[str, dict[str, str]]] = {}
    for label, entry in fuzzy_lookup:
        if len(normalize_key(label)) < 4:
            continue
        target_url = normalize_url(entry["url"])
        current = labels_by_url.get(target_url)
        if current is None or len(label) < len(current[0]):
            labels_by_url[target_url] = (label, entry)

    mention_index: list[tuple[str, dict[str, str], str, list[str]]] = []
    for target_url, (label, entry) in labels_by_url.items():
        mention_index.append((target_url, entry, label, key_variants(label)))
    mention_index.sort(key=lambda item: -len(item[2]))

    unlinked: dict[str, list[dict[str, str]]] = defaultdict(list)

    for page in pages:
        source_url = normalize_url(page.url)
        body = plain_bodies.get(source_url, "")
        if not body:
            continue
        body_lower = body.lower()
        body_compact = re.sub(r"\s+", "", body_lower)
        body_norm = normalize_key(body)
        linked_urls = outgoing_urls.get(source_url, set())
        seen_targets: set[str] = set()

        for target_url, entry, label, variants in mention_index:
            if target_url == source_url or target_url in linked_urls:
                continue
            if target_url in seen_targets:
                continue
            if not any(
                v in body_compact or v in body_norm or v in body_lower for v in variants
            ):
                continue
            if not label_mentioned_in_body(label, body):
                continue
            seen_targets.add(target_url)
            unlinked[source_url].append(
                {"title": entry["title"], "url": entry["url"], "label": label}
            )

    for url in unlinked:
        unlinked[url] = sorted(unlinked[url], key=lambda item: item["title"].lower())
    return dict(unlinked)


def preprocess_wikilinks(
    text: str,
    registry: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
) -> str:
    def repl(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        display = target.split("|", 1)[1].strip() if "|" in target else target.split("|", 1)[0].strip()
        entry = resolve_target(target, registry, fuzzy_lookup=fuzzy_lookup)
        if entry:
            return (
                f'<a href="{html.escape(entry["url"])}" class="wikilink">'
                f"{html.escape(display)}</a>"
            )
        return f'<span class="wikilink-missing">{html.escape(display)}</span>'

    return WIKILINK_PATTERN.sub(repl, text)
