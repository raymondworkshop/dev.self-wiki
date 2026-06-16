"""Resolve compression/wiki citations to raw excerpts for discovery packs."""

from __future__ import annotations

import re
from pathlib import Path

from compression_provenance import normalize_raw_link
from config import RAW_DIR, WORKSPACE_PATH
from query_retrieval import extract_key_lines

RAW_WIKILINK_RE = re.compile(
    r"(?:\(Source:\s*)?\[\[(raw/[^\]|]+)(?:\|[^\]]*)?\]\]",
    re.IGNORECASE,
)


def parse_raw_links_from_text(text: str) -> list[str]:
    """Extract unique raw/... paths from compression or wiki markdown."""

    seen: set[str] = set()
    out: list[str] = []
    for match in RAW_WIKILINK_RE.finditer(text):
        link = normalize_raw_link(match.group(1))
        if link not in seen:
            seen.add(link)
            out.append(link)
    return out


def collect_raw_links(samples: list[dict]) -> list[str]:
    """Union of raw links cited across sample excerpts."""

    seen: set[str] = set()
    out: list[str] = []
    for sample in samples:
        for link in sample.get("raw_links") or parse_raw_links_from_text(
            sample.get("excerpt", "")
        ):
            if link not in seen:
                seen.add(link)
                out.append(link)
    return out


def enrich_compression_samples(samples: list[dict]) -> list[dict]:
    """Attach parsed raw_links to each compression sample."""

    enriched: list[dict] = []
    for sample in samples:
        excerpt = sample.get("excerpt", "")
        enriched.append({**sample, "raw_links": parse_raw_links_from_text(excerpt)})
    return enriched


def resolve_raw_snippets(
    raw_links: list[str],
    *,
    query_terms: list[str] | None = None,
    max_lines: int = 15,
    max_files: int = 20,
) -> list[dict]:
    """Fetch tier-3 raw excerpts for cited paths (≤max_lines each)."""

    terms = query_terms or []
    snippets: list[dict] = []
    for link in raw_links[:max_files]:
        rel = link[len("raw/") :] if link.startswith("raw/") else link
        abs_path = RAW_DIR / rel
        if not abs_path.is_file():
            snippets.append({"raw_path": link, "error": "not_found"})
            continue
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            snippets.append({"raw_path": link, "error": str(exc)})
            continue
        lines = extract_key_lines(content, terms, max_lines=max_lines)
        snippets.append(
            {
                "raw_path": link,
                "excerpt": "\n".join(lines),
                "line_count": len(content.splitlines()),
            }
        )
    return snippets


def format_raw_snippets_section(snippets: list[dict]) -> str:
    """Markdown block for discovery pending user_message."""

    if not snippets:
        return ""
    parts = ["## Resolved raw excerpts (tier 3)\n"]
    for item in snippets:
        path = item["raw_path"]
        if item.get("error"):
            parts.append(f"### {path}\n(not found: {item['error']})\n")
            continue
        excerpt = item.get("excerpt", "").strip()
        if excerpt:
            parts.append(f"### {path}\n{excerpt}\n")
        else:
            parts.append(f"### {path}\n(empty excerpt)\n")
    return "\n".join(parts)


def wiki_query_terms(wiki_samples: list[dict], *, max_terms: int = 24) -> list[str]:
    """Lightweight terms from wiki titles for raw excerpt ranking."""

    terms: list[str] = []
    for sample in wiki_samples:
        path = sample.get("path", "")
        stem = Path(path).stem.replace("-", " ").replace("_", " ")
        for piece in re.split(r"[\s/]+", stem):
            piece = piece.strip()
            if len(piece) > 2 and piece.lower() not in {"wiki", "self"}:
                terms.append(piece.lower())
    return list(dict.fromkeys(terms))[:max_terms]
