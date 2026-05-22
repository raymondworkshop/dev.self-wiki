import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_PATH = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)
INDEX_PATH = WORKSPACE_PATH / "self-wiki" / "log" / "INDEX.json"
WIKI_ROOT = WORKSPACE_PATH / "self-wiki" / "wiki"
OUTPUT_ROOT = WORKSPACE_PATH / "self-wiki" / "outputs"

LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit")

# Local MLX context constraints
MAX_CONTEXT_TOKENS = int(os.environ.get("MAX_CONTEXT_TOKENS", "8092"))
RESERVED_OUTPUT_TOKENS = int(os.environ.get("RESERVED_OUTPUT_TOKENS", "1200"))
PROMPT_SAFETY_MARGIN = int(os.environ.get("PROMPT_SAFETY_MARGIN", "300"))
MAX_PROMPT_TOKENS = max(
    1024, MAX_CONTEXT_TOKENS - RESERVED_OUTPUT_TOKENS - PROMPT_SAFETY_MARGIN
)

# Query profiles based on your 3 recurring question families.
QUESTION_PROFILES: Dict[str, Dict[str, List[str]]] = {
    "values": {
        "triggers": [
            "what are my values",
            "my values",
            "core values",
            "价值观",
            "價值觀",
            "价值",
            "價值",
            "什麼對我重要",
            "what matters",
            "principles",
        ],
        "keywords": [
            "values",
            "value",
            "core",
            "principle",
            "meaning",
            "freedom",
            "responsibility",
            "contribution",
            "relationship",
            "purpose",
            "价值观",
            "價值觀",
            "价值",
            "價值",
            "原則",
            "原则",
            "意義",
            "意义",
            "自由",
            "責任",
            "责任",
            "貢獻",
            "贡献",
            "關係",
            "关系",
        ],
    },
    "personality_logic": {
        "triggers": [
            "personality",
            "character",
            "底层逻辑",
            "底層邏輯",
            "性格",
            "人格",
            "self-awareness",
            "self-perception",
            "operating logic",
        ],
        "keywords": [
            "personality",
            "character",
            "trait",
            "self-awareness",
            "self-perception",
            "identity",
            "decision",
            "control",
            "anxiety",
            "action",
            "reflection",
            "性格",
            "人格",
            "特质",
            "特質",
            "自我认知",
            "自我認知",
            "自我觉察",
            "自我覺察",
            "底层逻辑",
            "底層邏輯",
            "控制",
            "焦虑",
            "焦慮",
            "行动",
            "行動",
            "決策",
            "决策",
        ],
    },
    "swot": {
        "triggers": [
            "strength",
            "weakness",
            "blind spot",
            "blindspot",
            "优点",
            "優點",
            "弱点",
            "弱點",
            "盲点",
            "盲點",
            "长处",
            "長處",
            "短板",
            "不足",
        ],
        "keywords": [
            "strength",
            "weakness",
            "blind",
            "blind spot",
            "areas for improvement",
            "self-critique",
            "self-doubt",
            "execution",
            "indecision",
            "avoidance",
            "优点",
            "優點",
            "弱点",
            "弱點",
            "盲点",
            "盲點",
            "长处",
            "長處",
            "短板",
            "不足",
            "改进",
            "改進",
            "自我怀疑",
            "自我懷疑",
            "拖延",
            "逃避",
            "决策",
            "決策",
        ],
    },
    "general": {
        "triggers": [],
        "keywords": [
            "principle",
            "synthesis",
            "self",
            "growth",
            "relationship",
            "decision",
            "emotion",
            "cognitive",
            "原则",
            "原則",
            "成长",
            "成長",
            "关系",
            "關係",
            "情绪",
            "情緒",
            "认知",
            "認知",
        ],
    },
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate for budgeting: mixed CJK/EN ≈ chars/2.2 to chars/4.
    We use conservative chars/3 to avoid overflow.
    """
    return max(1, len(text) // 3)


def get_llm_response(
    messages: List[Dict[str, str]]
) -> str | None:
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or "no-key"
    )
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": RESERVED_OUTPUT_TOKENS,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.post(LLM_URL, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return None


def detect_language(query: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", query):
        return "Chinese"
    return "English"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def compute_profile_scores(query: str) -> Dict[str, int]:
    q = normalize_text(query)
    scores: Dict[str, int] = {}

    analyze_verbs = ["analyze", "analysis", "分析", "請分析", "请分析"]
    value_verbs = ["what are", "what is", "什麼", "是什么", "是什麼", "價值觀", "价值观"]

    for profile, cfg in QUESTION_PROFILES.items():
        if profile == "general":
            continue

        triggers = [t.lower() for t in cfg["triggers"] if t]
        keywords = [k.lower() for k in cfg["keywords"] if k]

        exact_hits = [t for t in triggers if t in q]
        keyword_hits = [k for k in keywords if k in q]

        score = 0
        # Strong signal: explicit phrase intent
        score += 3 * len(exact_hits)
        # Medium signal: term coverage
        score += len(keyword_hits)
        # Co-occurrence bonus: multiple profile-relevant cues
        if len(set(keyword_hits)) >= 2:
            score += 2

        # Intent-verb hints
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
    """Return (best_profile, strong_confidence, all_scores).

    Strong confidence rule:
    - best_score >= 6
    - and best_score - second_score >= 2
    """
    scores = compute_profile_scores(query)
    if not scores:
        return "general", False, {}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_profile, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score <= 0:
        return "general", False, scores

    strong = best_score >= 6 and (best_score - second_score) >= 2
    return best_profile, strong, scores


def llm_expand_keywords(query: str, profile: str) -> List[str]:
    """Optional MLX-assisted keyword expansion. Falls back safely if unavailable."""
    seed = ", ".join(QUESTION_PROFILES[profile]["keywords"][:20])
    prompt = (
        f"Query: {query}\n"
        f"Profile: {profile}\n"
        f"Seed terms: {seed}\n\n"
        "Return 12-24 concise bilingual retrieval keywords (Chinese + English), "
        "comma-separated only, no explanation. Include variants for principles, patterns, and behavior."
    )
    response = get_llm_response(prompt, "You are a precise terminology extractor.")
    if not response:
        return []

    tokens = [t.strip().lower() for t in re.split(r"[,\n]", response) if t.strip()]
    # Keep reasonable token lengths
    return [t for t in tokens if 1 < len(t) <= 48]


def deterministic_keywords(query: str, profile: str) -> List[str]:
    base = [t.lower() for t in QUESTION_PROFILES[profile]["keywords"]]
    parts = [p.lower() for p in re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]+", query)]
    return base + parts


def build_query_terms(query: str, profile: str) -> List[str]:
    terms = deterministic_keywords(query, profile)
    # Let local MLX improve recall, but keep deterministic safety.
    terms += llm_expand_keywords(query, profile)

    dedup = []
    seen = set()
    for t in terms:
        t = t.strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        dedup.append(t)

    return dedup[:80]


def score_topic(name: str, data: dict, query_terms: List[str], profile: str) -> int:
    name_l = name.lower()
    tags = [str(t).lower() for t in data.get("tags", [])]
    tag_blob = " ".join(tags)

    level = int(data.get("level", 0) or 0)
    score = level * 16  # Prefer higher-level distilled pages.

    # Type boosts
    if "type/principle" in tags:
        score += 18
    if "type/synthesis" in tags:
        score += 12
    if "type/shift" in tags:
        score += 8

    # Penalties for low-signal metadata/source-only pages
    if "type/source" in tags:
        score -= 6
    if any("metadata" in t for t in tags):
        score -= 12

    profile_terms = QUESTION_PROFILES[profile]["keywords"]
    for term in query_terms:
        if term in name_l:
            score += 28
        if term in tag_blob:
            score += 16

    # Slight bonus for profile-keyword/tag alignment
    for t in profile_terms:
        if t.lower() in tag_blob:
            score += 4

    return score


def extract_key_lines(
    content: str, query_terms: List[str], max_lines: int = 18
) -> List[str]:
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    selected: List[str] = []

    # Prioritize Socratic summary blockquotes and key headers.
    for ln in lines:
        if ln.startswith(">") and len(selected) < max_lines // 3:
            selected.append(ln)

    # Add lines matching query terms.
    qset = [t for t in query_terms if len(t) > 1]
    for ln in lines:
        lnl = ln.lower()
        if any(t in lnl for t in qset):
            if ln not in selected:
                selected.append(ln)
            if len(selected) >= max_lines:
                break

    # Fallback: first non-noisy lines.
    if len(selected) < 8:
        for ln in lines[:40]:
            if ln.startswith("---"):
                continue
            if ln not in selected:
                selected.append(ln)
            if len(selected) >= max_lines:
                break

    return selected[:max_lines]


def build_evidence_snippet(path: Path, query_terms: List[str]) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    lines = extract_key_lines(content, query_terms)
    filename = path.name
    body = "\n".join(f"- {ln}" for ln in lines)
    return f"### [[{filename}]]\n{body}\n"


def sanitize_filename(question: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", question).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return safe[:max_len] or "query"


def load_index() -> dict:
    if not INDEX_PATH.exists():
        raise FileNotFoundError("Index not found. Run 'make sync' first.")
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def matched_terms(
    name: str, data: dict, query_terms: List[str], top_n: int = 12
) -> List[str]:
    name_l = name.lower()
    tags = " ".join([str(t).lower() for t in data.get("tags", [])])
    hits = []
    for term in query_terms:
        if term in name_l or term in tags:
            hits.append(term)
    # de-dup keep order
    seen = set()
    ordered = []
    for h in hits:
        if h in seen:
            continue
        seen.add(h)
        ordered.append(h)
    return ordered[:top_n]


def rank_topics(
    index: dict, query_terms: List[str], profile: str
) -> List[Tuple[int, Path, str, dict]]:
    ranked: List[Tuple[int, Path, str, dict]] = []
    for name, data in index.get("topics", {}).items():
        rel_path = data.get("path")
        if not rel_path:
            continue
        f = WORKSPACE_PATH / rel_path
        if not f.exists() or f.suffix.lower() != ".md":
            continue

        score = score_topic(name, data, query_terms, profile)
        ranked.append((score, f, name, data))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked


def select_candidates(
    ranked: List[Tuple[int, Path, str, dict]], top_k: int = 16
) -> List[Tuple[int, Path, str, dict]]:
    if not ranked:
        return []

    # Keep a meaningful threshold to avoid noisy tail.
    floor = max(ranked[0][0] - 60, 1)
    filtered = [it for it in ranked if it[0] >= floor]
    return filtered[:top_k]


def trim_evidence_to_budget(
    query: str,
    profile: str,
    language: str,
    query_terms: List[str],
    snippets: List[str],
) -> str:
    """Fit evidence snippets into the prompt token budget.

    We keep snippets in ranked order and stop before exceeding MAX_PROMPT_TOKENS.
    """
    header = (
        f"Question: {query}\n"
        f"Detected profile: {profile}\n"
        f"Language: {language}\n"
        f"Retrieval terms: {', '.join(query_terms[:40])}\n\n"
        "Task:\n"
        "1) Answer strictly from the provided wiki evidence.\n"
        "2) Use this method implicitly: extract principles -> validate with repeated patterns -> then synthesize.\n"
        "3) Follow the profile-specific instruction.\n"
        "4) Include a concise 'Socratic Question' at the end.\n\n"
        "Output format (markdown):\n"
        f"- # {query}\n"
        "- > 2-3 sentence Socratic summary\n"
        "- ## Question\n"
        "- ## Answer\n"
        "- ## Provenance\n"
        "  - list sources as [[filename.md]]\n\n"
        "Evidence Pack:\n"
    )

    budget = MAX_PROMPT_TOKENS
    used = estimate_tokens(header)
    kept: List[str] = []

    for snip in snippets:
        t = estimate_tokens(snip)
        if used + t > budget:
            break
        kept.append(snip)
        used += t

    return "\n\n".join(kept)


def build_synthesis_prompt(
    query: str,
    profile: str,
    language: str,
    query_terms: List[str],
    evidence_block: str,
    strict_profile: bool,
) -> Tuple[str, str]:
    system_prompt = (
        "You are a Socratic analyst for a personal wiki. "
        "Ground every claim in provided wiki evidence. "
        "If inferring beyond explicit wording, label it [AI Synthesis]. "
        "If raising reflective challenge, label it [Socratic Observation]. "
        "Never invent sources."
    )

    strict_profile_instruction = {
        "values": "Identify 5-7 core values, explain each with evidence, and include tensions between values.",
        "personality_logic": "Analyze personality traits and underlying operating logic, including recurring loops and contradiction points.",
        "swot": "Provide three sections: strengths, weaknesses, blind spots. Each item must include evidence and one actionable correction.",
        "general": "Answer comprehensively with themes, implications, and practical next steps.",
    }[profile]

    flexible_instruction = (
        "Answer naturally based on evidence, using the structure that best fits the user's question. "
        "Do not force a rigid template unless clearly required by the question wording."
    )

    profile_instruction = (
        strict_profile_instruction if strict_profile else flexible_instruction
    )

    prompt = f"""
Question: {query}
Detected profile: {profile}
Language: {language}
Retrieval terms: {", ".join(query_terms[:40])}

Task:
1) Answer strictly from the provided wiki evidence.
2) Use this method implicitly: extract principles -> validate with repeated patterns -> then synthesize.
3) {profile_instruction}
4) Include a concise "Socratic Question" at the end.

Output format (markdown):
- # {query}
- > 2-3 sentence Socratic summary
- ## Question
- ## Answer
- ## Provenance
  - list sources as [[filename.md]]

Evidence Pack:
{evidence_block}
"""
    return system_prompt, prompt


def save_output(question: str, messages: List[Dict[str, str]]) -> Path:
    OUTPUT_ROOT.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_q = sanitize_filename(question)
    out = OUTPUT_ROOT / f"{safe_q}-{date_str}.md"

    # Filter out system prompt for better readability in the saved file
    dialogue = "\n\n".join([f"**{m['role'].capitalize()}**: {m['content']}" for m in messages if m['role'] != 'system'])

    note_content = f"""---
tags: [type/synthesis, query-wiki]
date: {date_str}
title: {question}
question: {question}
scope: self-wiki/wiki
---

{dialogue}
"""
    out.write_text(note_content, encoding="utf-8")
    return out


def print_intro_help():
    intro = f"""
query-wiki introduction
=======================

Purpose:
- Reason over self-wiki/wiki and answer life queries with provenance.
- Uses local MLX-compatible OpenAI API endpoint.

Current model config:
- LLM_URL   = {LLM_URL}
- LLM_MODEL = {LLM_MODEL}
- MAX_CONTEXT_TOKENS = {MAX_CONTEXT_TOKENS}
- RESERVED_OUTPUT_TOKENS = {RESERVED_OUTPUT_TOKENS}
- MAX_PROMPT_TOKENS = {MAX_PROMPT_TOKENS}

Built-in query logic:
1) Detect question profile:
   - values
   - personality_logic
   - swot (strengths/weaknesses/blind spots)
   - general
2) Score profile confidence (strong only if best>=6 and best-second>=2)
3) Build bilingual retrieval keywords (deterministic + optional MLX expansion)
3) Rank INDEX topics by level/tags/term-matches
4) Select high-signal candidates
5) Extract evidence snippets from wiki files
6) Synthesize answer with [AI Synthesis] / [Socratic Observation]
7) Save to self-wiki/outputs/{{question}}-{{date}}.md

Examples:
- python3 scripts/query_wiki.py "what are my values?"
- python3 scripts/query_wiki.py "請分析我的性格和底層邏輯"
- python3 scripts/query_wiki.py "分析我的優點，弱點，盲點" --debug-retrieval
- python3 scripts/query_wiki.py --list

Tips:
- Run `make sync` first if INDEX is missing.
- Use --debug-retrieval to inspect ranking scores and matched terms.
"""
    print(intro.strip())


def query_wiki(query: str | None, debug_retrieval: bool = False, list_mode: bool = False):
    if list_mode:
        index = load_index()
        print("Available topics:")
        print("\n".join(sorted(index.get("topics", {}).keys())))
        return

    # Initial setup
    try:
        index = load_index()
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    # If no initial query, start interactive loop
    if not query:
        print("Starting interactive session. Type 'quit' or 'exit' to finish.")
        messages = []
        while True:
            q = input("\nQuery: ").strip()
            if q.lower() in ["quit", "exit"]:
                break
            if not q:
                continue

            # For simplicity, treat each input as a fresh retrieval query,
            # or could append to context.
            perform_query_turn(q, index, messages, debug_retrieval)
        return

    # One-shot mode
    messages = []
    perform_query_turn(query, index, messages, debug_retrieval)

    # After one-shot, prompt for save
    save_choice = input("\nSave this conversation? [y/N]: ").strip().lower()
    if save_choice == 'y':
        out_path = save_output(query, messages)
        print(f"Conversation saved to {out_path}")

def perform_query_turn(query: str, index: dict, messages: List[Dict[str, str]], debug_retrieval: bool):
    profile, strong_profile, profile_scores = detect_profile_confidence(query)
    language = detect_language(query)
    query_terms = build_query_terms(query, profile)

    ranked = rank_topics(index, query_terms, profile)
    candidates = select_candidates(ranked, top_k=16)

    evidence_snippets = [
        build_evidence_snippet(p, query_terms) for _, p, _, _ in candidates
    ]
    evidence_block = trim_evidence_to_budget(
        query=query,
        profile=profile,
        language=language,
        query_terms=query_terms,
        snippets=evidence_snippets,
    )

    system_prompt, user_prompt = build_synthesis_prompt(
        query=query,
        profile=profile,
        language=language,
        query_terms=query_terms,
        evidence_block=evidence_block,
        strict_profile=strong_profile,
    )

    if not messages:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": user_prompt})

    answer = get_llm_response(messages)
    if not answer:
        logger.error("Failed to generate answer from LLM.")
        return

    print(f"\n--- ANSWER ---\n{answer}")
    messages.append({"role": "assistant", "content": answer})



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Query the self-wiki using local MLX.",
        epilog="Tip: use --intro for full query logic introduction and examples.",
    )
    parser.add_argument("query", nargs="?", help="Your question")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available indexed topics and exit.",
    )
    parser.add_argument(
        "--debug-retrieval",
        action="store_true",
        help="Print retrieval ranking scores, matched terms, and selected candidates.",
    )
    parser.add_argument(
        "--intro",
        action="store_true",
        help="Show introduction/help for query logic, profiles, and examples.",
    )

    args = parser.parse_args()

    if args.intro:
        print_intro_help()
        sys.exit(0)

    if not args.query and not args.list:
        print(
            'Usage: python3 scripts/query_wiki.py "Your question" [--debug-retrieval]'
        )
        print("Or:    python3 scripts/query_wiki.py --list")
        print("Use --intro for full introduction/help.")
        sys.exit(1)

    query_wiki(args.query, debug_retrieval=args.debug_retrieval, list_mode=args.list)
