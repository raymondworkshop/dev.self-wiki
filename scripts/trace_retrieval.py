"""Deterministic trace retrieval: keyword rank over raw paragraphs (no LLM, no vectors)."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_provider import context_limits, is_cloud_provider
from trace_index import ensure_index, load_index

logger = logging.getLogger(__name__)

# Source tier: authored posts ≫ personal notes ≫ twitter bookmarks.
KIND_BOOST = {
    "post": 48,
    "apple-notes": 12,
    "raw": 16,
    "twitter": -55,
}

_PATH_DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
_INLINE_SCOPE_RE = re.compile(r"(?:^|\s)@(?P<scope>\S+)\s*$")


def normalize_scope_token(scope: str | None) -> str | None:
    if not scope:
        return None
    s = str(scope).strip().strip("\"'").lstrip("@")
    s = s.replace("\\", "/")
    if s.startswith("self-wiki/"):
        s = s[len("self-wiki/") :]
    s = s.strip("/")
    return s or None


def parse_query_and_scope(query: str, scope: str | None = None) -> tuple[str, str | None]:
    """Split trailing @path from the question; explicit scope wins."""
    q = (query or "").strip()
    explicit = normalize_scope_token(scope)
    if explicit:
        return q, explicit
    m = _INLINE_SCOPE_RE.search(q)
    if not m:
        return q, None
    return q[: m.start()].strip(), normalize_scope_token(m.group("scope"))


def resolve_scope_paths(paragraphs: list[dict[str, Any]], scope: str) -> list[str]:
    """Match a file stem, filename, raw path, or directory prefix."""
    token = normalize_scope_token(scope)
    if not token:
        return []
    tl = token.lower()
    paths = sorted({(p.get("path") or "").replace("\\", "/") for p in paragraphs if p.get("path")})
    if not paths:
        return []

    def stem(p: str) -> str:
        return Path(p).stem.lower()

    exact = [p for p in paths if p.lower() == tl or p.lower().endswith("/" + tl)]
    if exact:
        return exact
    if not tl.endswith(".md"):
        by_stem = [p for p in paths if stem(p) == tl or stem(p) == tl.replace(".md", "")]
        if len(by_stem) == 1:
            return by_stem
        if by_stem:
            # Prefer _posts article over mirrors when ambiguous.
            posts = [p for p in by_stem if "/_posts/" in p and "/twitter/" not in p]
            return posts or by_stem
        by_file = [p for p in paths if p.lower().endswith("/" + tl + ".md")]
        if by_file:
            return by_file
    # Directory / prefix scope
    prefix_hits = [
        p
        for p in paths
        if p.lower() == tl
        or p.lower().startswith(tl.rstrip("/") + "/")
        or f"/{tl.rstrip('/')}/" in f"/{p.lower()}/"
    ]
    if prefix_hits:
        return prefix_hits
    # Loose contains (last resort)
    contains = [p for p in paths if tl in p.lower()]
    return contains


def _candidate_dict(para: dict[str, Any], score: int, *, kind: str | None = None) -> dict[str, Any]:
    k = kind or effective_kind(para)
    return {
        "id": para["id"],
        "path": para["path"],
        "file": para["file"],
        "para": para["para"],
        "start_line": para["start_line"],
        "end_line": para["end_line"],
        "kind": k,
        "score": score,
        "text": para.get("text") or "",
        "source_url": f"/source?id={para['id']}",
    }

# Light bilingual bridges for the concepts you actually query across ZH/EN notes.
TERM_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"自由", "freedom", "free"}),
    frozenset({"愛", "爱", "love", "loving"}),
    frozenset({"價值觀", "价值观", "values", "value"}),
    frozenset({"金錢", "金钱", "money", "wealth"}),
    frozenset({"恐懼", "恐惧", "fear"}),
    frozenset({"勇氣", "勇气", "courage"}),
)

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
        "什麼",
        "怎么",
        "怎麼",
        "如何",
        "是否",
        "哪个",
        "哪個",
        "哪些",
        "为什么",
        "為什麼",
        "一个",
        "一個",
        "一些",
        "这个",
        "這個",
        "那个",
        "那個",
        "还有",
        "還有",
        "以及",
        "或者",
        "是什么",
        "是什麼",
        "有哪些",
        "怎么样",
        "怎麼樣",
        "是不是",
        "可不可以",
        "麼是",
        "么是",
    }
)

# Trailing question/mood particles glued onto content (愛呢 → 愛).
_ZH_PARTICLES = frozenset("呢嗎吗嘛啊呀吧哇喔麼麽么欸耶啦")

# Peel common question frames so content words remain.
_ZH_Q_PREFIXES = (
    "什麼是",
    "什么是",
    "什麼叫",
    "什么叫",
    "如何定義",
    "如何定义",
    "怎樣才算",
    "怎样才算",
)
_ZH_Q_SUFFIXES = ("是什麼", "是什么", "是誰", "是谁", "怎麼樣", "怎么样")
_ZH_FUNC_UNIGRAMS = frozenset("的了著着在是與与和及或也又都就還还很太更最")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def detect_language(query: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", query):
        return "Chinese"
    return "English"


def _strip_zh_question_frame(run: str) -> str:
    """Reduce a Han run to content: 什麼是自由 → 自由, 愛呢 → 愛."""
    s = "".join(c for c in run if "\u4e00" <= c <= "\u9fff")
    while s and s[-1] in _ZH_PARTICLES:
        s = s[:-1]
    for pref in _ZH_Q_PREFIXES:
        if s.startswith(pref) and len(s) > len(pref):
            s = s[len(pref) :]
            break
    for suf in _ZH_Q_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
            break
    while s and s[-1] in _ZH_PARTICLES:
        s = s[:-1]
    return s


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


def _looks_like_frontmatter(text: str) -> bool:
    t = (text or "").lstrip()
    if not t.startswith("---"):
        return False
    head = t[:400].lower()
    return any(k in head for k in ("title:", "layout:", "related:", "date:", "categories:"))


def expand_query_terms(terms: list[str]) -> list[str]:
    """Add bilingual synonyms for known concept bridges (自由↔free/freedom)."""
    out: list[str] = []
    seen: set[str] = set()
    for t in terms:
        tl = t.lower().strip()
        if not tl or tl in seen:
            continue
        seen.add(tl)
        out.append(t)
    for t in list(out):
        tl = t.lower()
        for group in TERM_SYNONYM_GROUPS:
            if tl in group or t in group:
                for syn in group:
                    s = syn.lower()
                    if s not in seen:
                        seen.add(s)
                        out.append(syn)
                break
    return out


def query_primary_terms(query: str) -> list[str]:
    """Content terms from the question only (before synonym expansion)."""
    terms: list[str] = []
    seen: set[str] = set()

    def add(token: str, *, allow_unigram: bool = False) -> None:
        t = token.lower().strip()
        if not t or t in seen:
            return
        if len(t) == 1:
            if not allow_unigram:
                return
            if t in _ZH_PARTICLES or t in _ZH_FUNC_UNIGRAMS:
                return
            if not ("\u4e00" <= t <= "\u9fff"):
                return
        elif len(t) < 2:
            return
        if t in EN_STOPWORDS or t in ZH_STOPWORDS:
            return
        seen.add(t)
        terms.append(t)

    for word in re.findall(r"[a-zA-Z]+", query):
        add(word)

    for run in re.findall(r"[\u4e00-\u9fff]+", query):
        core = _strip_zh_question_frame(run)
        if not core:
            continue
        if len(core) == 1:
            add(core, allow_unigram=True)
            continue
        if 2 <= len(core) <= 6:
            add(core)
        for ng in _chinese_ngrams(core):
            add(ng)

    return terms


def query_literal_terms(query: str) -> list[str]:
    """Primary query terms plus bilingual synonyms."""
    return expand_query_terms(query_primary_terms(query))


def _term_weight(term: str) -> int:
    if re.search(r"[\u4e00-\u9fff]", term):
        if len(term) >= 4:
            return 14
        if len(term) == 3:
            return 12
        if len(term) == 1:
            return 11  # intentional content unigram (愛, 錢, …)
        return 7  # bigram — useful but noisier
    if len(term) >= 5:
        return 10
    if len(term) >= 4:
        return 8
    return 5


def effective_kind(para: dict[str, Any]) -> str:
    """Prefer path over stored kind so twitter/notes stay correctly tiered."""
    path = (para.get("path") or "").replace("\\", "/")
    if "/twitter/" in path or path.startswith("twitter/"):
        return "twitter"
    if (
        "apple-notes" in path
        or "/origin-apple-notes/" in path
        or path.startswith("origin-apple-notes/")
    ):
        return "apple-notes"
    if "/_posts/" in path or path.startswith("_posts/") or path.startswith("raw/_posts/"):
        return "post"
    return para.get("kind") or "raw"


def recency_boost(para: dict[str, Any], *, now: datetime | None = None) -> int:
    """Newer dated notes score higher; undated → 0."""
    path = para.get("path") or ""
    file_name = para.get("file") or ""
    m = _PATH_DATE_RE.search(file_name) or _PATH_DATE_RE.search(path)
    if not m:
        return 0
    try:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return 0
    days = ((now or datetime.now()) - dt).days
    if days < 0:
        days = 0
    if days <= 30:
        return 40
    if days <= 90:
        return 32
    if days <= 180:
        return 24
    if days <= 365:
        return 18
    if days <= 365 * 2:
        return 10
    if days <= 365 * 5:
        return 2
    if days <= 365 * 10:
        return -8
    return -18


def score_paragraph(
    para: dict[str, Any],
    query_terms: list[str],
    *,
    primary_terms: list[str] | None = None,
    now: datetime | None = None,
) -> int:
    if not query_terms:
        return 0
    primary = {t.lower() for t in (primary_terms or query_terms) if t}
    text = para.get("text") or ""
    text_l = text.lower()
    path_l = (para.get("path") or "").lower()
    file_l = (para.get("file") or "").lower()
    score = 0
    hit_terms = 0
    body_term_hits = 0
    primary_body_hits = 0
    for term in query_terms:
        if not term:
            continue
        is_primary = term.lower() in primary
        weight = _term_weight(term)
        if not is_primary:
            # Synonyms help recall but must not drown primary-language essays.
            weight = max(3, weight // 2)
        body_hits = text_l.count(term)
        matched = False
        if body_hits:
            cap = 8 if is_primary else 3
            score += min(body_hits, cap) * weight
            body_term_hits += body_hits
            if is_primary:
                primary_body_hits += body_hits
            matched = True
        # Path/file boost only for primary terms — synonyms like "free" must
        # match body text, otherwise a-free-man.md boosts every paragraph.
        if is_primary and term in path_l:
            score += weight * 2
            matched = True
        if is_primary and term in file_l and term not in path_l:
            score += weight
            matched = True
        if matched:
            hit_terms += 1
    if score <= 0:
        return 0
    if hit_terms >= 2:
        score += 20

    text_len = len(text.strip())
    if text_len >= 220:
        score += 28
    elif text_len >= 100:
        score += 16
    elif text_len >= 60:
        score += 8
    elif text_len < 40:
        score -= 40 if body_term_hits == 0 else 8

    if body_term_hits >= 3:
        score += 14
    if primary_body_hits >= 2:
        score += 18

    for line in text.splitlines()[:6]:
        s = line.strip()
        if s.startswith("#"):
            heading = s.lstrip("#").strip().lower()
            if any(term in heading for term in primary if term):
                score += 36
                break
            if any(term in heading for term in query_terms if term):
                score += 20
                break

    # Note filename about the concept (a-free-man) + body has primary term.
    if primary_body_hits:
        stem = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", file_l + path_l)
        for term in query_terms:
            tl = term.lower()
            if tl in primary or len(tl) < 3:
                continue
            if tl in stem:
                score += 48
                break

    if _looks_like_frontmatter(text):
        score -= 90

    kind = effective_kind(para)
    score += KIND_BOOST.get(kind, 1)
    score += recency_boost(para, now=now)
    return max(score, 1) if body_term_hits else max(score, 0)


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


def apply_neighbor_boost(
    scored: list[tuple[int, dict[str, Any]]],
    paragraphs: list[dict[str, Any]],
    *,
    radius: int = 2,
) -> list[tuple[int, dict[str, Any]]]:
    """Raise / admit ±radius siblings of keyword hits (same path).

    Neighbors get a fraction of the seed score so pack stays on-topic without
    dumping the whole file in reading order.
    """
    if not scored or radius < 1:
        return scored
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for p in paragraphs:
        path = (p.get("path") or "").replace("\\", "/")
        try:
            n = int(p.get("para") or 0)
        except (TypeError, ValueError):
            continue
        if path and n > 0:
            by_key[(path, n)] = p

    best: dict[str, tuple[int, dict[str, Any]]] = {}
    for score, para in scored:
        pid = para.get("id") or ""
        if not pid:
            continue
        prev = best.get(pid)
        if prev is None or score > prev[0]:
            best[pid] = (score, para)

    seeds = list(best.values())
    for seed_score, seed in seeds:
        path = (seed.get("path") or "").replace("\\", "/")
        try:
            n = int(seed.get("para") or 0)
        except (TypeError, ValueError):
            continue
        if not path or n <= 0:
            continue
        # Neighbors are context, not equals of the hit.
        neighbor_score = max(8, seed_score // 3)
        for delta in range(-radius, radius + 1):
            if delta == 0:
                continue
            nb = by_key.get((path, n + delta))
            if not nb:
                continue
            text = nb.get("text") or ""
            if _looks_like_frontmatter(text):
                continue
            pid = nb.get("id") or ""
            if not pid:
                continue
            prev = best.get(pid)
            if prev is None or neighbor_score > prev[0]:
                best[pid] = (neighbor_score, nb)

    out = list(best.values())
    out.sort(key=lambda x: (-x[0], x[1].get("path", ""), x[1].get("para", 0)))
    return out


def build_retrieval_pack(
    query: str,
    *,
    index: dict[str, Any] | None = None,
    provider: str | None = None,
    top_k: int | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    idx = index if index is not None else ensure_index()
    paragraphs = idx.get("paragraphs") or []
    query, scope_token = parse_query_and_scope(query, scope)
    scope_paths = resolve_scope_paths(paragraphs, scope_token) if scope_token else []
    scoped = bool(scope_token)
    if scoped:
        allow = set(scope_paths)
        paragraphs = [p for p in paragraphs if (p.get("path") or "").replace("\\", "/") in allow]

    primary = query_primary_terms(query) if query else []
    terms = expand_query_terms(primary) if primary else []
    language = detect_language(query) if query else "Chinese"

    scored: list[tuple[int, dict[str, Any]]] = []
    for para in paragraphs:
        if terms:
            s = score_paragraph(para, terms, primary_terms=primary)
            if s > 0:
                scored.append((s, para))
        elif scoped:
            # Doc-only + empty/generic question: skim in reading order (capped later).
            scored.append((1, para))
    scored.sort(key=lambda x: (-x[0], x[1].get("path", ""), x[1].get("para", 0)))

    # Single-doc: admit ±2 neighbors of hits instead of padding the whole file.
    if scoped and terms:
        radius_raw = os.environ.get("TRACE_SCOPE_NEIGHBOR_RADIUS", "").strip()
        radius = int(radius_raw) if radius_raw.isdigit() else 2
        scored = apply_neighbor_boost(scored, paragraphs, radius=radius)

    env_k = os.environ.get("TRACE_TOP_K", "").strip()
    scope_k = os.environ.get("TRACE_SCOPE_TOP_K", "").strip()
    if top_k is not None:
        limit = top_k
    elif scoped and scope_k.isdigit():
        limit = max(1, int(scope_k))
    elif env_k.isdigit():
        limit = max(1, int(env_k))
    elif scoped:
        # Precise packs beat dumping the whole note into the LLM.
        limit = 16 if is_cloud_provider(provider) else 12
    else:
        limit = 40 if is_cloud_provider(provider) else 32

    def _env_cap(name: str, default: int) -> int:
        raw = os.environ.get(name, "").strip()
        if raw.isdigit():
            return max(1, int(raw))
        return default

    cap_post = _env_cap("TRACE_MAX_PER_POST", 10)
    cap_notes = _env_cap("TRACE_MAX_PER_NOTES", 4)
    cap_twitter = _env_cap("TRACE_MAX_PER_TWITTER", 2)
    raw_global = os.environ.get("TRACE_MAX_PER_FILE", "").strip().lower()
    global_cap: int | None = None
    if raw_global.isdigit() and int(raw_global) > 0:
        global_cap = int(raw_global)

    _, _, max_prompt = context_limits(provider)
    budget = max(800, int(max_prompt * 0.55))

    selected: list[dict[str, Any]] = []
    used = 0
    evidence_parts: list[str] = []
    per_file: dict[str, int] = {}
    thin_notes = 0
    twitter_n = 0
    primary_l = [t.lower() for t in primary if t]
    selected_ids: set[str] = set()

    def try_add(score: int, para: dict[str, Any], *, honor_caps: bool) -> bool:
        nonlocal used, thin_notes, twitter_n
        path = para.get("path") or ""
        text = para.get("text") or ""
        text_l = text.lower()
        text_len = len(text.strip())
        kind = effective_kind(para)
        pid = para.get("id") or ""
        if pid in selected_ids:
            return False
        if _looks_like_frontmatter(text):
            return False
        if honor_caps and not scoped:
            if kind == "twitter" and twitter_n >= cap_twitter:
                return False
            if global_cap is not None:
                file_cap = global_cap
            elif kind == "post":
                file_cap = cap_post
            elif kind == "apple-notes":
                file_cap = cap_notes
            elif kind == "twitter":
                file_cap = cap_twitter
            else:
                file_cap = min(cap_post, 6)
            if primary_l and not any(t in text_l for t in primary_l):
                file_cap = min(file_cap, 2)
            file_cap = min(file_cap, limit)
            if per_file.get(path, 0) >= file_cap:
                return False
            if (
                kind == "apple-notes"
                and text_len < 60
                and thin_notes >= max(2, limit // 6)
            ):
                return False
        block = format_evidence_block({**para, "kind": kind})
        cost = estimate_tokens(block)
        if selected and used + cost > budget:
            return False
        if len(selected) >= limit:
            return False
        selected.append(_candidate_dict(para, score, kind=kind))
        evidence_parts.append(block)
        used += cost
        selected_ids.add(pid)
        per_file[path] = per_file.get(path, 0) + 1
        if kind == "twitter":
            twitter_n += 1
        if kind == "apple-notes" and text_len < 60:
            thin_notes += 1
        return True

    pool = scored if scoped else scored[: max(limit * 20, 200)]
    for score, para in pool:
        try_add(score, para, honor_caps=not scoped)

    if scoped and scope_token and not scope_paths:
        evidence_block = (
            f"(empty — scope {scope_token!r} matched no indexed raw/ paths)"
        )
    elif not selected:
        evidence_block = "(empty — no keyword matches in raw/)"
    else:
        evidence_block = "\n".join(evidence_parts)

    return {
        "query": query,
        "scope": scope_token,
        "scope_paths": scope_paths,
        "language": language,
        "query_terms": terms,
        "candidates": selected,
        "evidence_block": evidence_block,
        "evidence_tokens": used,
        "index_paragraph_count": len(paragraphs) if scoped else len(idx.get("paragraphs") or []),
        "index_built_at": idx.get("built_at"),
    }


def print_retrieval_debug(pack: dict[str, Any]) -> None:
    print("trace retrieval debug", flush=True)
    print(f"  language: {pack.get('language')}", flush=True)
    if pack.get("scope"):
        print(f"  scope: {pack.get('scope')}", flush=True)
        print(f"  scope_paths: {', '.join(pack.get('scope_paths') or [])}", flush=True)
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
    parser.add_argument("--scope", default=None, help="Limit to raw path / file stem / folder")
    args = parser.parse_args()
    pack = build_retrieval_pack(
        args.query, provider=args.provider, top_k=args.top_k, scope=args.scope
    )
    print_retrieval_debug(pack)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
