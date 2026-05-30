import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from llm_provider import context_limits, get_llm_response, model_name, provider_name

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_PATH = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)


def load_env():
    env_path = WORKSPACE_PATH / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

INDEX_PATH = WORKSPACE_PATH / "self-wiki" / "log" / "INDEX.json"
WIKI_ROOT = WORKSPACE_PATH / "self-wiki" / "wiki"
OUTPUT_ROOT = WORKSPACE_PATH / "self-wiki" / "outputs"

# LLM Configuration
LLM_PROVIDER = provider_name()
LLM_MODEL = model_name()
GEMINI_MODEL = model_name("gemini")
MAX_CONTEXT_TOKENS, RESERVED_OUTPUT_TOKENS, MAX_PROMPT_TOKENS = context_limits()

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
    value_verbs = [
        "what are",
        "what is",
        "什麼",
        "是什么",
        "是什麼",
        "價值觀",
        "价值观",
    ]

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
    - For personality_logic: best_score >= 5 (lower threshold for deeper analysis)
    - For other profiles: best_score >= 6 and best_score - second_score >= 2
    """
    scores = compute_profile_scores(query)
    if not scores:
        return "general", False, {}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_profile, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score <= 0:
        return "general", False, scores

    # Lower threshold for personality_logic to ensure deep analysis
    if best_profile == "personality_logic":
        strong = best_score >= 5
    else:
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
    messages = [
        {"role": "system", "content": "You are a precise terminology extractor."},
        {"role": "user", "content": prompt},
    ]
    response = get_llm_response(messages, max_tokens=RESERVED_OUTPUT_TOKENS)
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
    alias_l = str(data.get("alias", "")).lower()
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
        if term in name_l or (alias_l and term in alias_l):
            score += 28
        if term in tag_blob:
            score += 16

    # Slight bonus for profile-keyword/tag alignment
    for t in profile_terms:
        if t.lower() in tag_blob:
            score += 4

    return score


def extract_key_lines(
    content: str, query_terms: List[str], max_lines: int = 15
) -> List[str]:
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    selected: List[str] = []

    # 1. Prioritize Socratic summary blockquotes (high signal)
    for ln in lines:
        if ln.startswith(">") and len(selected) < 3:
            selected.append(ln)

    # 2. Add high-signal headers and their direct children
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

    # 3. Add lines with explicit provenance markers
    for ln in lines:
        if ("(source: [[" in ln.lower() or "[[raw/" in ln.lower()) and len(
            selected
        ) < 10:
            if ln not in selected:
                selected.append(ln)

    # 4. Add lines matching query terms
    qset = [t for t in query_terms if len(t) > 1]
    for ln in lines:
        lnl = ln.lower()
        if any(t in lnl for t in qset):
            if ln not in selected:
                selected.append(ln)
            if len(selected) >= max_lines:
                break

    return selected[:max_lines]


def build_evidence_snippet(path: Path, query_terms: List[str]) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        # Increase lines per snippet for Gemini to provide richer context
        lines_budget = 40 if LLM_PROVIDER == "gemini" else 15
        lines = extract_key_lines(content, query_terms, max_lines=lines_budget)
        try:
            source_ref = str(path.relative_to(WORKSPACE_PATH))
        except ValueError:
            source_ref = str(path)
        body = "\n".join(lines)
        return f"### [[{source_ref}]]\n{body}\n"
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return ""


def sanitize_filename(question: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", question).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return safe[:max_len] or "query"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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
    # de-dup keep order
    seen = set()
    ordered = []
    for h in hits:
        if h in seen:
            continue
        seen.add(h)
        ordered.append(h)
    return ordered[:top_n]


def iter_wiki_files() -> List[Path]:
    if not WIKI_ROOT.exists():
        logger.warning(f"Wiki root not found: {WIKI_ROOT}")
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
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return 0

    text_l = content.lower()
    name_l = path.stem.lower()
    profile_terms = {t.lower() for t in QUESTION_PROFILES[profile]["keywords"]}
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
    top_k: int = 40 if LLM_PROVIDER == "gemini" else 16,
) -> List[Tuple[int, Path, str, dict]]:
    if not ranked:
        return []

    # Keep a meaningful threshold to avoid noisy tail.
    # For Gemini, we allow a wider tail to capture more nuance.
    threshold_diff = 150 if LLM_PROVIDER == "gemini" else 60
    floor = max(ranked[0][0] - threshold_diff, 1)
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
        "4) Include one concise 'Socratic Question' at the end.\n\n"
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
        "You are a Socratic analyst for a personal wiki, acting as a 'Reasoning Engine' and a 'Socratic Mirror'. "
        "Ground every claim in provided wiki evidence. "
        "Every key claim must carry an inline source reference from the Evidence Pack. "
        "Match the user's input language perfectly (Chinese or English). "
        "If inferring beyond explicit wording, label it [AI Synthesis]. "
        "If raising reflective challenge or identifying a blind spot/bias, label it [Socratic Observation]. "
        "If identifying a significant change in belief or contradiction, flag it as a [Cognitive Shift]. "
        "Trace claims back to original raw sources whenever available in evidence. "
        "Never invent sources, filenames, raw paths, dates, events, or preferences."
    )

    # Protocols from GEMINI.md
    protocols = """
    Interaction Protocols:
    - Deep Analysis: Subject -> Analysis Framework -> Key Insights -> Implications -> Socratic Question.
    - Comparison: Entity A vs Entity B -> Overlap -> Divergence -> Synthesis/Conclusion.
    - Recommendation: Context -> Options (Max 3) -> Rationale -> Potential Pitfalls.
    """

    strict_profile_instruction = {
        "values": "Perform a 'Deep Analysis' of my core values. Identify 5-7 core values, explain each with evidence, and explore the tensions between them. Incorporate a Mermaid diagram to visualize the value system and provide specific 'Next Steps' for value-aligned living.",
        "personality_logic": """Analyze my personality traits and underlying operating logic using a 'Deep Analysis' approach. Your goal is to produce a high-resolution, multi-dimensional report similar to a professional character audit.

Key Sections to include:
1. **Core Personality Portrait**: Identify 5-7 fundamental traits with direct wiki evidence.
2. **Underlying Operating Logic**: Explain 3-5 core beliefs that drive behaviors.
3. **Internal Tensions & Paradoxes**: Map the contradictions (e.g., control vs. freedom).
4. **Mermaid Structure Map**: A graph (e.g., graph TD) visualizing the personality/logic system.
5. **Actionable Upgrades (Next Steps)**: 3-5 specific, evidence-based recommendations for growth.

Requirements:
- Use abundant [AI Synthesis] and [Socratic Observation] labels.
- Every claim must carry inline source markers: (Source: [[filename.md]]).
- Conclude with 1-2 high-impact Socratic Questions.""",
        "swot": "Perform a self-audit. Categorize findings into Strengths, Weaknesses, and Blind Spots. Each finding must include evidence and one actionable correction. Use a structured, report-like format and include a summary 'Next Steps' section.",
        "general": "Answer comprehensively. If the question involves complex analysis, comparison, or recommendation, apply the corresponding Interaction Protocol (Deep Analysis, Comparison, or Recommendation). Use a Mermaid diagram if it clarifies the synthesis and always provide 'Next Steps'.",
    }[profile]

    flexible_instruction = (
        "Answer naturally based on evidence, using a professional, report-like structure. "
        "Apply the most relevant Interaction Protocol (Deep Analysis, Comparison, or Recommendation) if applicable. "
        "Include a Mermaid diagram to visualize complex relationships and always provide 'Next Steps'."
    )

    profile_instruction = (
        strict_profile_instruction if strict_profile else flexible_instruction
    )

    prompt = f"""
Question: {query}
Detected profile: {profile}
Language: {language}
Retrieval terms: {", ".join(query_terms[:40])}

{protocols}

Task:
1) Answer strictly from the provided wiki evidence.
2) Use this method implicitly: extract principles -> validate with repeated patterns -> then synthesize.
3) {profile_instruction}
4) Include one or two high-impact "Socratic Questions" at the end. These questions should be heuristic and designed to pierce through surface behaviors to elicit your 'bottom-level logic' (底层逻辑) or expose hidden cognitive contradictions.
5) Ensure all headers and summaries align with the Socratic Mirror philosophy.
6) Provenance rules:
   - Add an inline source marker after every key factual claim, interpretation, value, pattern, or recommendation, e.g. (Source: [[self-wiki/wiki/example.md]]).
   - If a source line contains a raw origin reference, prefer that raw source in the inline marker; otherwise cite the Evidence Pack page.
   - If multiple sources support one claim, cite the strongest 2-3 sources.
   - If evidence is weak, say "Insufficient wiki evidence" instead of answering confidently.
   - Do not cite files or raw paths that are not visible in the Evidence Pack.

Output format (markdown):
- # {query}
- > 2-3 sentence Socratic summary
- ## Analysis / Answer
- ## Provenance
  - list each cited source once, with a 1-sentence note explaining what evidence it contributed

Evidence Pack:
{evidence_block or "[No evidence snippets were retrieved. Say that the wiki evidence is insufficient instead of inventing an answer.]"}
"""
    return system_prompt, prompt


def save_output(question: str, messages: List[Dict[str, str]]) -> Path:
    OUTPUT_ROOT.mkdir(exist_ok=True)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    last_updated = now.isoformat(timespec="seconds")
    safe_q = sanitize_filename(question)
    out = OUTPUT_ROOT / f"{safe_q}-{date_str}.md"

    # Filter out system prompt for better readability in the saved file
    dialogue = "\n\n".join(
        [
            f"**{m['role'].capitalize()}**: {m['content']}"
            for m in messages
            if m["role"] != "system"
        ]
    )

    note_content = f"""---
last_updated: {last_updated}
title: {yaml_string(question)}
description: {yaml_string(f"Query-wiki synthesis generated from self-wiki evidence for: {question}")}
level: 1
tags: [type/synthesis, query-wiki]
date: {date_str}
question: {yaml_string(question)}
scope: self-wiki/wiki
---

> This query note captures a reasoning snapshot generated from the curated wiki evidence available at query time. Treat confident claims as valid only when they carry provenance back to the cited wiki or raw sources.
> It is a Level 1 synthesis artifact: useful for reflection and follow-up, but not a replacement for the underlying source notes.

## Query

{question}

## Conversation

{dialogue}

## Evolution

- {date_str}: Created by `query-wiki` from the current `self-wiki/wiki` index and retrieved evidence snippets.

## Backlinks

- **Evolved from**: [[self-wiki/wiki]]
- **Mentioned in**: [[GEMINI.md]]
- **Contradicts**: None identified in this query output.
"""
    out.write_text(note_content, encoding="utf-8")
    return out


def print_intro_help():
    intro = f"""
query-wiki introduction
=======================

Purpose:
- Reason over self-wiki/wiki and answer life queries with provenance.
- Supports Local MLX (OpenAI-compatible) and Google Gemini API.

Current model config:
- LLM_PROVIDER = {LLM_PROVIDER}
- LLM_MODEL    = {LLM_MODEL} (MLX/OpenAI)
- GEMINI_MODEL = {GEMINI_MODEL}
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
4) Rank full-text wiki matches plus INDEX metadata when available
5) Select high-signal candidates
6) Extract evidence snippets from wiki files
7) Synthesize answer with [AI Synthesis] / [Socratic Observation] / [Cognitive Shift]
8) Apply Interaction Protocols (Deep Analysis, Comparison, Recommendation)
9) Save to self-wiki/outputs/{{question}}-{{date}}.md


Examples:
- python3 scripts/query_wiki.py "what are my values?"
- python3 scripts/query_wiki.py "請分析我的性格和底層邏輯"
- python3 scripts/query_wiki.py "分析我的優點，弱點，盲點" --debug-retrieval
- python3 scripts/query_wiki.py --list

Tips:
- Run `make sync` to refresh INDEX metadata; query falls back to full-text scan if INDEX is missing.
- Use --debug-retrieval to inspect ranking scores and matched terms.
"""
    print(intro.strip())


def query_wiki(
    query: str | None, debug_retrieval: bool = False, list_mode: bool = False
):
    if list_mode:
        index = load_index(required=False)
        print("Available topics:")
        topics = sorted(index.get("topics", {}).keys())
        if topics:
            print("\n".join(topics))
        else:
            print("\n".join(str(p.relative_to(WIKI_ROOT)) for p in iter_wiki_files()))
        return

    # Initial setup
    index = load_index(required=False)
    messages = []
    first_query = query

    # If initial query provided, run one-shot turn
    if query:
        perform_query_turn(query, index, messages, debug_retrieval)

    # Start interactive loop if no query or continue after initial query
    print("Starting interactive session. Type 'quit' or 'exit' to finish.")
    while True:
        q = input("\nQuery: ").strip()
        if q.lower() in ["quit", "exit"]:
            break
        if not q:
            continue

        if not first_query:
            first_query = q

        perform_query_turn(q, index, messages, debug_retrieval)

    # Prompt to save after exiting
    if len(messages) > 0 and first_query:
        save_choice = input("\nSave this conversation? [y/N]: ").strip().lower()
        if save_choice == "y":
            out_path = save_output(first_query, messages)
            print(f"Conversation saved to {out_path}")
    return


def perform_query_turn(
    query: str, index: dict, messages: List[Dict[str, str]], debug_retrieval: bool
):
    profile, strong_profile, profile_scores = detect_profile_confidence(query)
    language = detect_language(query)
    query_terms = build_query_terms(query, profile)

    ranked = rank_wiki_candidates(index, query, query_terms, profile)
    candidates = select_candidates(ranked, top_k=16)

    if debug_retrieval:
        print("\n--- RETRIEVAL DEBUG ---")
        print(f"profile={profile}, strong_profile={strong_profile}")
        print(f"profile_scores={profile_scores}")
        print(f"query_terms={', '.join(query_terms[:40])}")
        for score, path, name, data in candidates:
            try:
                ref = path.relative_to(WORKSPACE_PATH)
            except ValueError:
                ref = path
            hits = matched_terms(name, data, query_terms)
            hit_text = f" | matched metadata terms: {', '.join(hits)}" if hits else ""
            print(f"{score:4d} | {ref}{hit_text}")

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

    answer = get_llm_response(messages, max_tokens=RESERVED_OUTPUT_TOKENS)
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
