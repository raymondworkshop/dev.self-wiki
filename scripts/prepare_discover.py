"""Prepare discovery evidence pack (deterministic, no LLM)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from config import COMPRESSION_DIR, PENDING_DIR, WIKI_DIR, WORKSPACE_PATH
from discover_provenance import (
    collect_raw_links,
    enrich_compression_samples,
    format_raw_snippets_section,
    resolve_raw_snippets,
    wiki_query_terms,
)
from llm_provider import context_limits, provider_name
from query_retrieval import estimate_tokens, trim_evidence_to_budget
from skill_registry import resolve_skill

logger = logging.getLogger(__name__)

SKILL_INSTRUCTION_RESERVE_TOKENS = 1500


def _excerpt_limit(provider: str | None) -> int:
    name = provider_name(provider)
    return 800 if name == "mlx" else 2000


def _sample_from_dir(directory: Path, limit: int, *, excerpt_limit: int = 2000) -> list[dict]:
    if not directory.exists() or limit <= 0:
        return []
    files = sorted(directory.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    samples: list[dict] = []
    for path in files[:limit]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(WORKSPACE_PATH)).replace("\\", "/")
        samples.append({"path": rel, "excerpt": text[:excerpt_limit]})
    return samples


def _stratified_compression_samples(
    *, total_limit: int = 50, excerpt_limit: int = 2000
) -> list[dict]:
    """Sample across lanes — avoid twitter-only packs when those files are newest."""

    strata: list[tuple[str, int]] = [
        ("_posts/new-apple-notes", 10),
        ("_posts/learning", 10),
        ("_posts/diary", 8),
        ("_posts/self", 8),
        ("_posts/notes", 6),
        ("_posts/philosophy", 4),
        ("_posts/research", 4),
        ("origin-apple-notes", 10),
        ("twitter", 8),
    ]
    seen: set[str] = set()
    out: list[dict] = []
    for rel_dir, cap in strata:
        base = COMPRESSION_DIR / rel_dir
        for item in _sample_from_dir(base, cap, excerpt_limit=excerpt_limit):
            if item["path"] in seen:
                continue
            seen.add(item["path"])
            out.append(item)
            if len(out) >= total_limit:
                return out
    return out


def _sample_files(
    directory: Path, limit: int = 40, *, excerpt_limit: int = 2000
) -> list[dict]:
    return _sample_from_dir(directory, limit, excerpt_limit=excerpt_limit)


def _compression_snippet(sample: dict) -> str:
    header = f"### {sample['path']}\n"
    if sample.get("raw_links"):
        header += f"raw_links: {', '.join(sample['raw_links'])}\n"
    return header + sample["excerpt"]


def _wiki_snippet(sample: dict) -> str:
    return f"### {sample['path']}\n{sample['excerpt']}"


def _build_budgeted_user_message(
    *,
    provider: str | None,
    compression_samples: list[dict],
    wiki_samples: list[dict],
    raw_snippets: list[dict],
) -> str:
    _, _, max_prompt = context_limits(provider)
    budget = max(1024, max_prompt - SKILL_INSTRUCTION_RESERVE_TOKENS)

    header = (
        f"Discovery run {datetime.now().date().isoformat()}\n"
        f"Provider hint: {provider_name(provider)}\n\n"
    )
    header_tokens = estimate_tokens(header)
    section_overhead = estimate_tokens("## Compression samples\n\n## Wiki samples\n\n")

    compression_snippets = [_compression_snippet(s) for s in compression_samples]
    wiki_snippets = [_wiki_snippet(s) for s in wiki_samples]
    raw_section = format_raw_snippets_section(raw_snippets)
    raw_snippets_list = [raw_section] if raw_section.strip() else []

    total_before = len(compression_snippets) + len(wiki_snippets) + len(raw_snippets_list)

    trimmed_compression = trim_evidence_to_budget(
        compression_snippets,
        provider=provider,
        max_prompt_tokens=budget - header_tokens - section_overhead,
    )
    remaining = budget - header_tokens - section_overhead - estimate_tokens(trimmed_compression)

    trimmed_wiki = trim_evidence_to_budget(
        wiki_snippets,
        provider=provider,
        max_prompt_tokens=max(256, remaining),
    )
    remaining -= estimate_tokens(trimmed_wiki)

    trimmed_raw = trim_evidence_to_budget(
        raw_snippets_list,
        provider=provider,
        max_prompt_tokens=max(256, remaining),
    )

    def _snippet_count(text: str) -> int:
        if not text:
            return 0
        return text.count("\n### ") + (1 if text.startswith("### ") else 0)

    total_after = (
        _snippet_count(trimmed_compression)
        + _snippet_count(trimmed_wiki)
        + _snippet_count(trimmed_raw)
    )
    if total_after < total_before:
        logger.info(
            "Discovery evidence trimmed for %s: %d sections → %d (budget ~%d tokens)",
            provider_name(provider),
            total_before,
            total_after,
            budget,
        )

    parts = [header.rstrip(), "## Compression samples"]
    if trimmed_compression:
        parts.append(trimmed_compression)
    parts.append("## Wiki samples")
    if trimmed_wiki:
        parts.append(trimmed_wiki)
    if trimmed_raw:
        parts.append(trimmed_raw)
    return "\n\n".join(parts) + "\n"


def write_pending(*, provider: str | None = None) -> Path:
    excerpt_limit = _excerpt_limit(provider)
    compression_samples = enrich_compression_samples(
        _stratified_compression_samples(total_limit=50, excerpt_limit=excerpt_limit)
    )
    wiki_samples = _sample_files(WIKI_DIR, limit=20, excerpt_limit=excerpt_limit)
    query_terms = wiki_query_terms(wiki_samples)
    raw_links = collect_raw_links(compression_samples)
    raw_snippets = resolve_raw_snippets(
        raw_links,
        query_terms=query_terms,
        max_lines=15,
        max_files=20,
    )
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pending_path = PENDING_DIR / f"discover-{ts}.json"
    user_message = _build_budgeted_user_message(
        provider=provider,
        compression_samples=compression_samples,
        wiki_samples=wiki_samples,
        raw_snippets=raw_snippets,
    )
    out_name = f"self-wiki/discovery/{datetime.now().date().isoformat()}.md"
    payload = {
        "kind": "discovery",
        "skill": resolve_skill("discovery", "skills/discovery.md"),
        "user_message": user_message,
        "output_file": out_name,
        "created_at": datetime.now().isoformat(),
        "resolved_raw": raw_snippets,
        "raw_link_count": len(raw_links),
    }
    pending_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return pending_path
