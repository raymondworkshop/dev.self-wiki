"""Wikilink resolution for vault pages."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Sequence

from memex.config import (
    CJK_RE,
    FUZZY_MIN_SCORE,
    FUZZY_SCORE_GAP,
    QUOTE_CHARS,
    SHORT_QUERY_MAX_LEN,
)
from memex.search_expand import expand_for_search
from memex.sources import DATED_STEM_SUFFIX, VaultPage, get_aliases, slugify


def register_target(
    registry: dict[str, dict[str, str]],
    title: str,
    url: str,
    *,
    stem: str | None = None,
    aliases: Sequence[str] | None = None,
    rel: str | None = None,
) -> None:
    entry = {"url": url, "title": title, "rel": rel or ""}
    registry[title.lower().strip()] = entry
    registry[slugify(title)] = entry
    if stem:
        registry[stem.lower().strip()] = entry
    if rel:
        registry[rel] = entry
        registry[Path(rel).name] = entry
        registry[Path(rel).stem] = entry
    for alias in aliases or ():
        alias = alias.strip()
        if alias:
            registry[alias.lower()] = entry
            registry[slugify(alias)] = entry


def normalize_key(text: str) -> str:
    text = text.strip().lstrip("!").strip()
    text = text.strip(QUOTE_CHARS)
    return re.sub(r"\s+", " ", text).lower()


def key_variants(text: str) -> list[str]:
    base = normalize_key(text)
    if not base:
        return []
    variants = [base]
    if CJK_RE.search(base):
        for line in expand_for_search(base).split("\n"):
            line = line.strip().lower()
            if line and line not in variants:
                variants.append(line)
    return variants


def normalize_url(url: str) -> str:
    url = url.strip().split("#", 1)[0].split("?", 1)[0]
    if url.endswith("/index.html"):
        url = url[: -len("/index.html")] or "/"
    if url.endswith("/") and len(url) > 1:
        url = url.rstrip("/")
    return url


def normalize_link_target(raw: str) -> str:
    target = raw.split("|", 1)[0].strip()
    for prefix in ("self-wiki/", "../", "./"):
        if target.startswith(prefix):
            target = target.removeprefix(prefix)
    if not target.endswith(".md") and "/" in target and not target.endswith("/"):
        if "." not in Path(target).name:
            target = f"{target}.md"
    return target


def build_url_registry(registry: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for entry in registry.values():
        out[normalize_url(entry["url"])] = entry
    return out


def build_fuzzy_lookup(pages: list[VaultPage]) -> list[tuple[str, dict[str, str]]]:
    seen: set[tuple[str, str]] = set()
    lookup: list[tuple[str, dict[str, str]]] = []
    for page in pages:
        entry = {"url": page.url, "title": page.title, "rel": page.rel}
        labels = [page.title, page.stem, *get_aliases(page)]
        dated = DATED_STEM_SUFFIX.match(page.stem)
        if dated:
            labels.append(dated.group(1))
        for label in labels:
            label = str(label).strip()
            if not label:
                continue
            key = (normalize_key(label), entry["url"])
            if key in seen:
                continue
            seen.add(key)
            lookup.append((label, entry))
    return lookup


def _word_boundary_match(query: str, label: str) -> bool:
    q = normalize_key(query)
    l = normalize_key(label)
    if not q or not l:
        return False
    if CJK_RE.search(q) or CJK_RE.search(l):
        return any(v in l for v in key_variants(query))
    pattern = r"(?<!\w)" + re.escape(q) + r"(?!\w)"
    return bool(re.search(pattern, l))


def score_fuzzy(
    query: str,
    label: str,
    *,
    backlink_count: int = 0,
) -> int:
    q = normalize_key(query)
    l = normalize_key(label)
    if not q or not l:
        return 0
    q_vars = key_variants(query)
    l_vars = key_variants(label)
    if any(a == b for a in q_vars for b in l_vars):
        score = 100
    elif len(q) <= SHORT_QUERY_MAX_LEN:
        score = 80 if any(b.startswith(a) for a in q_vars for b in l_vars) else 0
    elif any(b.startswith(a) for a in q_vars for b in l_vars):
        score = 80 + int(len(q) / max(len(l), 1) * 10)
    elif _word_boundary_match(query, label):
        score = 70
    elif any(a in b for a in q_vars for b in l_vars):
        score = 50 + int(len(q) / max(len(l), 1) * 20)
    else:
        return 0
    if not score:
        return 0
    score += max(0, 10 - min(len(l), 10))
    score += min(backlink_count, 20)
    return score


def resolve_candidates(
    raw: str,
    registry: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
    backlink_counts: dict[str, int] | None = None,
    min_score: int = FUZZY_MIN_SCORE,
    return_all: bool = False,
) -> list[tuple[dict[str, str], int, str]]:
    target = normalize_link_target(raw.split("|", 1)[0].strip())
    label = raw.split("|", 1)[1].strip() if "|" in raw else target

    for candidate in (target, label, Path(target).stem, Path(target).name):
        if candidate in registry:
            return [(registry[candidate], 100, candidate)]
        low = candidate.lower()
        if low in registry:
            return [(registry[low], 100, candidate)]

    for variant in key_variants(target):
        if variant in registry:
            return [(registry[variant], 100, variant)]

    if not fuzzy_lookup:
        return []

    backlink_counts = backlink_counts or {}
    best: dict[str, tuple[dict[str, str], int, str]] = {}
    for lbl, entry in fuzzy_lookup:
        url = normalize_url(entry["url"])
        score = score_fuzzy(target, lbl, backlink_count=backlink_counts.get(url, 0))
        if score < min_score:
            continue
        cur = best.get(url)
        if cur is None or score > cur[1]:
            best[url] = (entry, score, lbl)

    ranked = sorted(best.values(), key=lambda x: (-x[1], x[0]["title"].lower()))
    if not ranked:
        return []

    if return_all:
        return ranked

    top = ranked[0]
    if len(ranked) == 1 or top[1] - ranked[1][1] >= FUZZY_SCORE_GAP:
        return [top]
    return ranked


def resolve_target(
    raw: str,
    registry: dict[str, dict[str, str]],
    *,
    fuzzy_lookup: list[tuple[str, dict[str, str]]] | None = None,
    backlink_counts: dict[str, int] | None = None,
) -> dict[str, str] | None:
    candidates = resolve_candidates(
        raw,
        registry,
        fuzzy_lookup=fuzzy_lookup,
        backlink_counts=backlink_counts,
    )
    if not candidates:
        return None
    top = candidates[0]
    if len(candidates) == 1:
        return top[0]
    if top[1] - candidates[1][1] >= FUZZY_SCORE_GAP:
        return top[0]
    return None
