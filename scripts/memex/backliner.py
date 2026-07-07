"""Typed wiki backlink edges: Evolved from, Mentioned in, Contradicts."""

from __future__ import annotations

from pathlib import Path
from collections import defaultdict
from typing import Any

from memex.config import CONTRADICT_KEYWORDS, EVOLUTION_PATTERN, SOURCE_TRAIL_RE, WIKILINK_PATTERN
from memex.resolve import normalize_url, resolve_target
from memex.sources import VaultPage, strip_backlinks_block

TYPED_RELATIONS = ("Evolved from", "Mentioned in", "Contradicts")


def _wiki_pages(pages: list[VaultPage]) -> list[VaultPage]:
    skip = {"INDEX.md", "audit.md"}
    return [
        p
        for p in pages
        if p.layer == "wiki"
        and not p.rel.endswith("-Hub.md")
        and Path(p.rel).name not in skip
    ]


def build_typed_edges(
    wiki_pages: list[VaultPage],
    registry: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Map page_url -> relation -> list of {title, url, rel}."""

    typed: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: {rel: [] for rel in TYPED_RELATIONS}
    )
    seen: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {rel: set() for rel in TYPED_RELATIONS}
    )

    for page in wiki_pages:
        content = strip_backlinks_block(page.body)
        source_url = normalize_url(page.url)
        source_ref = {"title": page.title, "url": page.url, "rel": page.rel}
        evolution_match = EVOLUTION_PATTERN.search(content)
        evolution_text = evolution_match.group(1) if evolution_match else ""
        lines = content.splitlines()

        for match in WIKILINK_PATTERN.finditer(content):
            link_text = match.group(1).strip()
            link_display = link_text.split("|", 1)[0].strip()
            entry = resolve_target(link_text, registry, fuzzy_lookup=fuzzy_lookup)
            if not entry:
                continue
            target_url = normalize_url(entry["url"])
            if target_url == source_url:
                continue
            target_ref = {
                "title": entry["title"],
                "url": entry["url"],
                "rel": entry.get("rel", ""),
            }
            target_key = entry.get("rel") or entry["title"]

            if page.stem not in seen[target_url]["Mentioned in"]:
                seen[target_url]["Mentioned in"].add(page.stem)
                typed[target_url]["Mentioned in"].append(source_ref)

            in_evolution = (
                f"[[{link_display}]]" in evolution_text or f"[[{link_text}]]" in evolution_text
            )
            if in_evolution and target_key not in seen[source_url]["Evolved from"]:
                seen[source_url]["Evolved from"].add(target_key)
                typed[source_url]["Evolved from"].append(target_ref)

            for line in lines:
                if line.strip().startswith("#"):
                    continue
                if f"[[{link_display}]]" not in line and f"[[{link_text}]]" not in line:
                    continue
                body = SOURCE_TRAIL_RE.sub("", line).strip()
                if f"[[{link_display}]]" not in body and f"[[{link_text}]]" not in body:
                    continue
                prose = WIKILINK_PATTERN.sub("", body).strip()
                if any(kw in prose.lower() for kw in CONTRADICT_KEYWORDS):
                    if target_key not in seen[source_url]["Contradicts"]:
                        seen[source_url]["Contradicts"].add(target_key)
                        typed[source_url]["Contradicts"].append(target_ref)
                    break

    for url in typed:
        for rel in TYPED_RELATIONS:
            typed[url][rel] = sorted(typed[url][rel], key=lambda x: x["title"].lower())

    return dict(typed)


def get_typed_for_url(ctx: dict[str, Any], url: str) -> dict[str, list[dict[str, str]]]:
    return ctx.get("typed_backlinks", {}).get(normalize_url(url), {})
