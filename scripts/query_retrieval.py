"""Deterministic query retrieval: profiles, ranking, evidence extraction (no LLM)."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from config import INDEX_JSON, QUERY_PROFILES, WIKI_DIR, WORKSPACE_PATH
from llm_provider import context_limits, normalize_provider, provider_name

logger = logging.getLogger(__name__)

WIKI_ROOT = WIKI_DIR
INDEX_PATH = INDEX_JSON
OUTPUT_ROOT = WORKSPACE_PATH / "self-wiki" / "outputs"


@lru_cache(maxsize=1)
def load_profiles_config() -> dict:
    if not QUERY_PROFILES.exists():
        raise FileNotFoundError(f"Query profiles not found: {QUERY_PROFILES}")
    data = yaml.safe_load(QUERY_PROFILES.read_text(encoding="utf-8")) or {}
    return data


def question_profiles() -> Dict[str, Dict[str, list]]:
    return load_profiles_config().get("profiles", {})


def flexible_instruction() -> str:
    return load_profiles_config().get("flexible_instruction", "")


def profile_instruction(profile: str, *, strict: bool) -> str:
    cfg = load_profiles_config()
    profiles = cfg.get("profiles", {})
    if profile in profiles and profile != "general":
        if strict:
            return profiles[profile].get("strict_instruction", "")
        strict_text = profiles[profile].get("strict_instruction", "")
        if strict_text:
            flexible = cfg.get("flexible_instruction", "")
            return f"{flexible}\n\nProfile guidance ({profile}):\n{strict_text}"
    return cfg.get("flexible_instruction", "")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def detect_language(query: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", query):
        return "Chinese"
    return "English"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def compute_profile_scores(query: str) -> Dict[str, int]:
    q = normalize_text(query)
    scores: Dict[str, int] = {}
    profiles = question_profiles()

    analyze_verbs = ["analyze", "analysis", "分析", "請分析", "请分析"]
    value_verbs = [
        "what are",
        "what is",
        "什麼",
        "是什么",
        "是什麼",
        "價值觀",
        "价值观",
    ]

    for profile, cfg in profiles.items():
        if profile == "general":
            continue

        triggers = [t.lower() for t in cfg.get("triggers", []) if t]
        keywords = [k.lower() for k in cfg.get("keywords", []) if k]

        exact_hits = [t for t in triggers if t in q]
        keyword_hits = [k for k in keywords if k in q]

        score = 0
        score += 3 * len(exact_hits)
        score += len(keyword_hits)
        if len(set(keyword_hits)) >= 2:
            score += 2

        if any(v.lower() in q for v in analyze_verbs) and profile in (
            "personality_logic",
            "swot",
        ):
            score += 1
        if any(v.lower() in q for v in value_verbs) and profile == "values":
            score += 1

        scores[profile] = score

    return scores


def detect_profile_confidence(query: str) -> Tuple[str, bool, Dict[str, int]]:
    scores = compute_profile_scores(query)
    if not scores:
        return "general", False, {}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_profile, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score <= 0:
        return "general", False, scores

    if best_profile == "personality_logic":
        strong = best_score >= 5
    else:
        strong = best_score >= 6 and (best_score - second_score) >= 2
    return best_profile, strong, scores


def deterministic_keywords(query: str, profile: str) -> List[str]:
    profiles = question_profiles()
    base = [t.lower() for t in profiles[profile]["keywords"]]
    parts = [p.lower() for p in re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]+", query)]
    return base + parts


def build_query_terms(query: str, profile: str) -> List[str]:
    """Deterministic retrieval terms only (no LLM expansion)."""
    terms = deterministic_keywords(query, profile)
    dedup: List[str] = []
    seen: set[str] = set()
    for t in terms:
        t = t.strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        dedup.append(t)
    return dedup[:80]


def score_topic(name: str, data: dict, query_terms: List[str], profile: str) -> int:
    name_l = name.lower()
    alias_l = str(data.get("alias", "")).lower()
    tags = [str(t).lower() for t in data.get("tags", [])]
    tag_blob = " ".join(tags)

    level = int(data.get("level", 0) or 0)
    score = level * 16

    if "type/principle" in tags:
        score += 18
    if "type/synthesis" in tags:
        score += 12
    if "type/shift" in tags:
        score += 8
    if "type/source" in tags:
        score -= 6
    if any("metadata" in t for t in tags):
        score -= 12

    profile_terms = question_profiles()[profile]["keywords"]
    for term in query_terms:
        if term in name_l or (alias_l and term in alias_l):
            score += 28
        if term in tag_blob:
            score += 16

    for t in profile_terms:
        if t.lower() in tag_blob:
            score += 4

    return score


def extract_key_lines(
    content: str, query_terms: List[str], max_lines: int = 15
) -> List[str]:
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    selected: List[str] = []

    for ln in lines:
        if ln.startswith(">") and len(selected) < 3:
            selected.append(ln)

    in_high_signal = False
    for ln in lines:
        if ln.startswith("## "):
            lower_h = ln.lower()
            if any(
                term in lower_h
                for term in ["evolution", "source", "principle", "shift", "insight"]
            ):
                in_high_signal = True
                if ln not in selected:
                    selected.append(ln)
            else:
                in_high_signal = False
        elif in_high_signal and (ln.startswith("-") or ln.startswith("*")):
            if ln not in selected:
                selected.append(ln)
            if len(selected) >= 8:
                in_high_signal = False

    for ln in lines:
        if ("(source: [[" in ln.lower() or "[[raw/" in ln.lower()) and len(
            selected
        ) < 10:
            if ln not in selected:
                selected.append(ln)

    qset = [t for t in query_terms if len(t) > 1]
    for ln in lines:
        lnl = ln.lower()
        if any(t in lnl for t in qset):
            if ln not in selected:
                selected.append(ln)
            if len(selected) >= max_lines:
                break

    return selected[:max_lines]


def build_evidence_snippet(
    path: Path, query_terms: List[str], *, provider: str | None = None
) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines_budget = (
            40 if normalize_provider(provider) in {"gemini", "openai"} else 15
        )
        lines = extract_key_lines(content, query_terms, max_lines=lines_budget)
        try:
            source_ref = str(path.relative_to(WORKSPACE_PATH))
        except ValueError:
            source_ref = str(path)
        body = "\n".join(lines)
        return f"### [[{source_ref}]]\n{body}\n"
    except Exception as exc:
        logger.error("Error reading %s: %s", path, exc)
        return ""


def load_index(required: bool = True) -> dict:
    if not INDEX_PATH.exists():
        if required:
            raise FileNotFoundError("Index not found. Run 'make sync' first.")
        logger.warning(
            "Index not found. Falling back to full-text wiki scan. Run 'make sync' to rebuild INDEX.json."
        )
        return {"topics": {}}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def matched_terms(
    name: str, data: dict, query_terms: List[str], top_n: int = 12
) -> List[str]:
    name_l = name.lower()
    alias_l = str(data.get("alias", "")).lower()
    tags = " ".join([str(t).lower() for t in data.get("tags", [])])
    hits = []
    for term in query_terms:
        if term in name_l or (alias_l and term in alias_l) or term in tags:
            hits.append(term)
    seen: set[str] = set()
    ordered: List[str] = []
    for h in hits:
        if h in seen:
            continue
        seen.add(h)
        ordered.append(h)
    return ordered[:top_n]


def iter_wiki_files() -> List[Path]:
    if not WIKI_ROOT.exists():
        logger.warning("Wiki root not found: %s", WIKI_ROOT)
        return []
    return sorted(p for p in WIKI_ROOT.rglob("*.md") if p.is_file())


def query_literal_terms(query: str) -> List[str]:
    return [
        p.lower()
        for p in re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]+", query)
        if len(p.strip()) > 1
    ]


def score_fulltext(path: Path, query: str, query_terms: List[str], profile: str) -> int:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.error("Error reading %s: %s", path, exc)
        return 0

    text_l = content.lower()
    name_l = path.stem.lower()
    profile_terms = {t.lower() for t in question_profiles()[profile]["keywords"]}
    literal_terms = set(query_literal_terms(query))

    headers = "\n".join(ln.lower() for ln in content.splitlines() if ln.startswith("#"))
    blockquotes = "\n".join(
        ln.lower() for ln in content.splitlines() if ln.startswith(">")
    )

    score = 0
    for term in query_terms:
        term = term.strip().lower()
        if len(term) <= 1:
            continue

        if term in literal_terms:
            weight = 8
        elif term in profile_terms:
            weight = 2
        else:
            weight = 4

        body_hits = text_l.count(term)
        if body_hits == 0 and term not in name_l:
            continue

        if term in name_l:
            score += weight * 12
        if term in headers:
            score += weight * 8
        if term in blockquotes:
            score += weight * 6
        score += min(body_hits, 3) * weight

    if score > 0:
        if re.search(r"^>\s", content, re.MULTILINE):
            score += 4
        if re.search(r"^##\s+Evolution\b", content, re.MULTILINE | re.IGNORECASE):
            score += 3
        if re.search(r"\(Source:\s*\[\[|^-\s*\[\[", content, re.MULTILINE):
            score += 3

    return score


def rank_wiki_candidates(
    index: dict, query: str, query_terms: List[str], profile: str
) -> List[Tuple[int, Path, str, dict]]:
    candidates: Dict[str, Dict[str, object]] = {}

    for name, data in index.get("topics", {}).items():
        rel_path = data.get("path")
        if not rel_path:
            continue
        f = WORKSPACE_PATH / rel_path
        if not f.exists() or f.suffix.lower() != ".md":
            continue

        score = score_topic(name, data, query_terms, profile)
        key = str(f.resolve())
        candidates[key] = {
            "score": score,
            "path": f,
            "name": name,
            "data": data,
            "metadata_score": score,
            "fulltext_score": 0,
        }

    for f in iter_wiki_files():
        score = score_fulltext(f, query, query_terms, profile)
        if score <= 0:
            continue

        key = str(f.resolve())
        if key in candidates:
            candidates[key]["score"] = int(candidates[key]["score"]) + score
            candidates[key]["fulltext_score"] = score
        else:
            candidates[key] = {
                "score": score,
                "path": f,
                "name": f.stem,
                "data": {"path": str(f.relative_to(WORKSPACE_PATH)), "tags": []},
                "metadata_score": 0,
                "fulltext_score": score,
            }

    ranked = [
        (int(item["score"]), item["path"], str(item["name"]), item["data"])
        for item in candidates.values()
    ]
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked


def select_candidates(
    ranked: List[Tuple[int, Path, str, dict]],
    *,
    provider: str | None = None,
    top_k: int | None = None,
) -> List[Tuple[int, Path, str, dict]]:
    if not ranked:
        return []

    llm_provider = normalize_provider(provider)
    if top_k is None:
        top_k = 40 if llm_provider == "gemini" else 16

    threshold_diff = 150 if llm_provider == "gemini" else 60
    floor = max(ranked[0][0] - threshold_diff, 1)
    filtered = [it for it in ranked if it[0] >= floor]
    return filtered[:top_k]


def trim_evidence_to_budget(
    snippets: List[str],
    *,
    provider: str | None = None,
    max_prompt_tokens: int | None = None,
) -> str:
    llm_provider = normalize_provider(provider)
    _, _, default_budget = context_limits(llm_provider)
    budget = max_prompt_tokens if max_prompt_tokens is not None else default_budget

    used = 0
    kept: List[str] = []
    for snip in snippets:
        t = estimate_tokens(snip)
        if used + t > budget:
            break
        kept.append(snip)
        used += t

    return "\n\n".join(kept)


def build_retrieval_pack(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
) -> dict:
    """Build retrieval metadata + evidence block (deterministic, no LLM)."""
    llm_provider = normalize_provider(provider)
    _, _, max_prompt_tokens = context_limits(llm_provider)
    index = index if index is not None else load_index(required=False)

    profile, strong_profile, profile_scores = detect_profile_confidence(query)
    language = detect_language(query)
    query_terms = build_query_terms(query, profile)
    instruction = profile_instruction(profile, strict=strong_profile)

    ranked = rank_wiki_candidates(index, query, query_terms, profile)
    candidates = select_candidates(ranked, provider=llm_provider)

    debug_rows = []
    for score, path, name, data in candidates:
        try:
            ref = path.relative_to(WORKSPACE_PATH)
        except ValueError:
            ref = path
        hits = matched_terms(name, data, query_terms)
        debug_rows.append(
            {
                "score": score,
                "path": str(ref),
                "name": name,
                "matched_terms": hits,
            }
        )

    evidence_snippets = []
    for _, p, _, _ in candidates:
        snip = build_evidence_snippet(p, query_terms, provider=llm_provider)
        if snip:
            evidence_snippets.append(snip)

    evidence_block = trim_evidence_to_budget(
        evidence_snippets,
        provider=llm_provider,
        max_prompt_tokens=max_prompt_tokens,
    )

    if not evidence_block:
        evidence_block = (
            "[No evidence snippets were retrieved. Say that the wiki evidence is insufficient "
            "instead of inventing an answer.]"
        )

    return {
        "query": query,
        "profile": profile,
        "strong_profile": strong_profile,
        "profile_scores": profile_scores,
        "language": language,
        "query_terms": query_terms,
        "profile_instruction": instruction,
        "candidates": debug_rows,
        "evidence_block": evidence_block,
        "provider": llm_provider,
    }


def print_retrieval_debug(pack: dict) -> None:
    print("\n--- RETRIEVAL DEBUG ---")
    print(f"profile={pack['profile']}, strong_profile={pack['strong_profile']}")
    print(f"profile_scores={pack['profile_scores']}")
    print(f"query_terms={', '.join(pack['query_terms'][:40])}")
    for row in pack["candidates"]:
        hit_text = (
            f" | matched metadata terms: {', '.join(row['matched_terms'])}"
            if row["matched_terms"]
            else ""
        )
        print(f"{row['score']:4d} | {row['path']}{hit_text}")
