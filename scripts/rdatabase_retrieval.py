"""Deterministic rdatabase retrieval: keyword rank over raw paragraphs (no LLM, no vectors)."""

from __future__ import annotations

import logging
import re
from typing import Any

from llm_provider import context_limits, is_cloud_provider
from rdatabase_index import ensure_index, load_index

logger = logging.getLogger(__name__)

KIND_BOOST = {
    "post": 12,
    "apple-notes": 10,
    "raw": 8,
    "twitter": -8,
}

EN_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "am",
        "i",
        "me",
        "my",
        "mine",
        "we",
        "our",
        "you",
        "your",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "what",
        "which",
        "who",
        "whom",
        "how",
        "when",
        "where",
        "why",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "would",
        "will",
        "with",
        "from",
        "as",
        "at",
        "by",
        "about",
    }
)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def detect_language(query: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", query):
        return "Chinese"
    return "English"


def query_literal_terms(query: str) -> list[str]:
    terms = [
        p.lower()
        for p in re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]+", query)
        if len(p.strip()) > 1
    ]
    filtered = [t for t in terms if t not in EN_STOPWORDS]
    return filtered or terms


def score_paragraph(para: dict[str, Any], query_terms: list[str]) -> int:
    if not query_terms:
        return 0
    text_l = (para.get("text") or "").lower()
    path_l = (para.get("path") or "").lower()
    file_l = (para.get("file") or "").lower()
    score = 0
    hit_terms = 0
    for term in query_terms:
        if len(term) <= 1:
            continue
        # Prefer distinctive terms (longer / Chinese)
        if re.search(r"[\u4e00-\u9fff]", term):
            weight = 12
        elif len(term) >= 5:
            weight = 10
        elif len(term) >= 4:
            weight = 8
        else:
            weight = 5
        body_hits = text_l.count(term)
        matched = False
        if body_hits:
            score += min(body_hits, 5) * weight
            matched = True
        if term in path_l:
            score += weight * 6
            matched = True
        if term in file_l:
            score += weight * 5
            matched = True
        if matched:
            hit_terms += 1
    if score <= 0:
        return 0
    if hit_terms >= 2:
        score += 20
    score += KIND_BOOST.get(para.get("kind") or "raw", 1)
    return score


def format_evidence_block(para: dict[str, Any]) -> str:
    path = para["path"]
    return (
        f"### [[{path}]] · #{para['id'].split('#')[-1]} · "
        f"L{para['start_line']}–L{para['end_line']} · kind: {para.get('kind', 'raw')}\n"
        f"path: {path}\n"
        f"file: {para['file']}\n"
        f"id: {para['id']}\n"
        f"> {para['text'].replace(chr(10), chr(10) + '> ')}\n"
    )


def build_retrieval_pack(
    query: str,
    *,
    index: dict[str, Any] | None = None,
    provider: str | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    idx = index if index is not None else ensure_index()
    paragraphs = idx.get("paragraphs") or []
    terms = query_literal_terms(query)
    language = detect_language(query)

    scored: list[tuple[int, dict[str, Any]]] = []
    for para in paragraphs:
        s = score_paragraph(para, terms)
        if s > 0:
            scored.append((s, para))
    scored.sort(key=lambda x: (-x[0], x[1].get("path", ""), x[1].get("para", 0)))

    default_k = 40 if is_cloud_provider(provider) else 20
    limit = top_k if top_k is not None else default_k
    _, _, max_prompt = context_limits(provider)
    # Reserve headroom for skill + question
    budget = max(800, int(max_prompt * 0.65))

    selected: list[dict[str, Any]] = []
    used = 0
    evidence_parts: list[str] = []
    for score, para in scored[: max(limit * 3, limit)]:
        block = format_evidence_block(para)
        cost = estimate_tokens(block)
        if selected and used + cost > budget:
            break
        if len(selected) >= limit:
            break
        selected.append(
            {
                "id": para["id"],
                "path": para["path"],
                "file": para["file"],
                "para": para["para"],
                "start_line": para["start_line"],
                "end_line": para["end_line"],
                "kind": para.get("kind"),
                "score": score,
                "source_url": f"/source?id={para['id']}",
            }
        )
        evidence_parts.append(block)
        used += cost

    evidence_block = "\n".join(evidence_parts) if evidence_parts else "(empty — no keyword matches in raw/)"

    return {
        "query": query,
        "language": language,
        "query_terms": terms,
        "candidates": selected,
        "evidence_block": evidence_block,
        "evidence_tokens": used,
        "index_paragraph_count": len(paragraphs),
        "index_built_at": idx.get("built_at"),
    }


def print_retrieval_debug(pack: dict[str, Any]) -> None:
    print("rdatabase retrieval debug", flush=True)
    print(f"  language: {pack.get('language')}", flush=True)
    print(f"  terms: {', '.join(pack.get('query_terms') or [])}", flush=True)
    print(
        f"  index: {pack.get('index_paragraph_count')} paragraphs "
        f"(built {pack.get('index_built_at')})",
        flush=True,
    )
    print(f"  evidence_tokens≈{pack.get('evidence_tokens')}", flush=True)
    for i, c in enumerate(pack.get("candidates") or [], start=1):
        print(
            f"  {i:02d}. score={c['score']} {c['id']} "
            f"({c['file']} L{c['start_line']}–L{c['end_line']} kind={c.get('kind')})",
            flush=True,
        )


def main() -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Debug rdatabase keyword retrieval")
    parser.add_argument("query")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()
    pack = build_retrieval_pack(args.query, provider=args.provider, top_k=args.top_k)
    print_retrieval_debug(pack)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
