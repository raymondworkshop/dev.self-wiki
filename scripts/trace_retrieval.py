"""Deterministic trace retrieval: keyword rank over raw paragraphs (no LLM, no vectors)."""

from __future__ import annotations

import logging
import re
from typing import Any

from llm_provider import context_limits, is_cloud_provider
from trace_index import ensure_index, load_index

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

# Light Chinese function/question fragments — keep retrieval on content words.
ZH_STOPWORDS = frozenset(
    {
        "我的",
        "你的",
        "他的",
        "她的",
        "我们",
        "你们",
        "他们",
        "什么",
        "怎么",
        "如何",
        "是否",
        "哪个",
        "哪些",
        "为什么",
        "一个",
        "一些",
        "这个",
        "那个",
        "还有",
        "以及",
        "或者",
        "是什么",
        "有哪些",
        "怎么样",
        "是不是",
        "可不可以",
    }
)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def detect_language(query: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", query):
        return "Chinese"
    return "English"


def _chinese_ngrams(run: str) -> list[str]:
    """Bigrams + trigrams over a contiguous Han run (order: longer first)."""
    chars = [c for c in run if "\u4e00" <= c <= "\u9fff"]
    if len(chars) < 2:
        return []
    out: list[str] = []
    if len(chars) >= 3:
        for i in range(len(chars) - 2):
            out.append("".join(chars[i : i + 3]))
    for i in range(len(chars) - 1):
        out.append("".join(chars[i : i + 2]))
    return out


def query_literal_terms(query: str) -> list[str]:
    """English words + Chinese short phrases / 2–3-grams (not whole questions as one term)."""
    terms: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        t = token.lower().strip()
        if len(t) <= 1 or t in seen:
            return
        if t in EN_STOPWORDS or t in ZH_STOPWORDS:
            return
        seen.add(t)
        terms.append(t)

    for word in re.findall(r"[a-zA-Z]+", query):
        add(word)

    for run in re.findall(r"[\u4e00-\u9fff]+", query):
        if len(run) <= 1:
            continue
        # Keep short contiguous phrases as exact terms (e.g. 价值观, 亲密关系).
        if 2 <= len(run) <= 6:
            add(run)
        for ng in _chinese_ngrams(run):
            add(ng)

    return terms


def _term_weight(term: str) -> int:
    if re.search(r"[\u4e00-\u9fff]", term):
        if len(term) >= 4:
            return 14
        if len(term) == 3:
            return 12
        return 7  # bigram — useful but noisier
    if len(term) >= 5:
        return 10
    if len(term) >= 4:
        return 8
    return 5


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
        weight = _term_weight(term)
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
                "text": para.get("text") or "",
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
    print("trace retrieval debug", flush=True)
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
    parser = argparse.ArgumentParser(description="Debug trace keyword retrieval")
    parser.add_argument("query")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()
    pack = build_retrieval_pack(args.query, provider=args.provider, top_k=args.top_k)
    print_retrieval_debug(pack)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
