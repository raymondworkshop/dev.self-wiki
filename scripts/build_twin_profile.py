"""Deterministic digital twin snapshot from Level-2 wiki pages."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from config import (
    TWIN_PRINCIPLES_JSON,
    TWIN_PROFILE,
    TWIN_SELF_HYPOTHESES,
    WIKI_DIR,
    WORKSPACE_PATH,
    twin_profile_max_evolution,
    twin_profile_max_principles,
    workspace_relpath,
)
from memex.config import HTML_COMMENT_RE

logger = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.7
EVOLUTION_LINE_RE = re.compile(r"^-\s*(\d{4}(?:-\d{2}-\d{2})?)\s*:\s*(.+?)\s*$")
# Provenance / ingest noise — never surface in PROFILE Recent evolution.
EVOLUTION_NOISE_RE = re.compile(
    r"distilled\s+from|from\s+raw\s+source|溯源自|来自\s*\[\[?\s*raw/",
    re.IGNORECASE,
)
EVOLUTION_SIGNAL_TERMS = (
    "promoted",
    "cognitive shift",
    "revised",
    "contradict",
    "migrat",
    "转化",
    "转变",
    "认知转变",
    "认知转移",
    "认知冲突",
)
# Personal belief corpus (exclude twitter bookmarks).
RAW_GROUNDING_RE = re.compile(
    r"raw/(?:origin-apple-notes|_posts|new-apple-notes)/",
    re.IGNORECASE,
)
COEXISTENCE_TERMS = (
    "并存",
    "张力",
    "尚未合成",
    "dual",
    "unreconciled",
    "tension",
    "contradict",
    "cognitive shift",
    "两条话语",
    "桥接",
    "未调和",
)
HYPOTHESIS_INCLUDE_STATUSES = frozenset({"supported"})
HYPOTHESIS_INCLUDE_JUDGMENTS = frozenset({"supported", "revised", "accepted"})
HYPOTHESIS_EXCLUDE = frozenset({"rejected"})
HYPOTHESIS_HEADING_RE = re.compile(r"^##\s+(H-[a-f0-9]+)\s*:\s*(.+?)\s*$", re.I)
OPERATING_RULE_PREFIX_RE = re.compile(
    r"^\*\*Operating rule:\*\*\s*", re.IGNORECASE
)
PRINCIPLE_DEDUP_THRESHOLD = 0.30
TOPIC_GROUP_ORDER = (
    "topic/leadership",
    "topic/relationships",
    "topic/connection",
    "topic/business",
    "topic/incentive",
    "topic/career",
    "topic/systems",
    "topic/wiki",
    "topic/learning",
    "topic/self-growth",
    "topic/softskills",
    "topic/vulnerability",
    "topic/wealth",
    "topic/invest",
    "topic/social",
    "topic/network",
)


def _parse_front_matter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def _tags_list(meta: dict) -> list[str]:
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        return [tags]
    return [str(t) for t in tags]


def _confidence(meta: dict) -> float:
    try:
        return float(meta.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _summary_line(content: str) -> str:
    m = re.search(r"^>\s*(.+?)(?:\n\n|\n##|\Z)", content, re.DOTALL | re.MULTILINE)
    if not m:
        return ""
    line = re.sub(r"\s+", " ", m.group(1).strip())
    return line[:240] + ("…" if len(line) > 240 else "")


def _wiki_rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE_PATH))


def _grounded_in_personal_raw(content: str) -> bool:
    """Principle must trace to personal raw (posts / apple-notes), not twitter."""
    return bool(RAW_GROUNDING_RE.search(content))


def _qualifies_principle(meta: dict, content: str = "") -> bool:
    level = int(meta.get("level", 0) or 0)
    confidence = _confidence(meta)
    if confidence <= 0 and level >= 2:
        confidence = 0.85
    if level < 2:
        return False
    if confidence < CONFIDENCE_FLOOR:
        return False
    tags = _tags_list(meta)
    if "type/principle" not in tags:
        return False
    if content and _grounded_in_personal_raw(content):
        return True
    if content and "discovery/" in content:
        return True
    return False


def _principle_sort_key(item: dict) -> tuple:
    return (
        -int(item.get("level", 0) or 0),
        -float(item.get("confidence", 0) or 0),
        str(item.get("last_updated", "")),
    )


def _strip_operating_rule_prefix(summary: str) -> str:
    return OPERATING_RULE_PREFIX_RE.sub("", (summary or "").strip()).strip()


def _rule_core(summary: str, *, max_len: int = 72) -> str:
    """First clause of an operating-rule summary for essence / similarity."""
    text = _strip_operating_rule_prefix(summary)
    text = re.sub(r"\s+", " ", text).strip()
    for sep in ("；", "。", ";", "."):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _content_tokens(text: str) -> set[str]:
    """English words + Chinese character bigrams (no CJK word segmenter)."""
    cleaned = _strip_operating_rule_prefix(text).lower()
    tokens: set[str] = set()
    for match in re.finditer(r"[a-z][a-z\-]+|[\u4e00-\u9fff]+", cleaned):
        chunk = match.group(0)
        if chunk.isascii():
            tokens.add(chunk)
            continue
        if len(chunk) == 1:
            tokens.add(chunk)
            continue
        tokens.update(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap_coeff(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _summary_similarity(a: str, b: str) -> float:
    """Overlap coefficient on Chinese bigrams + English tokens."""
    return _overlap_coeff(_content_tokens(a), _content_tokens(b))


def _principle_affinity(left: dict, right: dict) -> float:
    """Near-dup score: summary/title overlap, with same-topic bonus."""
    summary_score = _summary_similarity(
        left.get("summary") or "", right.get("summary") or ""
    )
    title_score = _overlap_coeff(
        _content_tokens(left.get("title") or ""),
        _content_tokens(right.get("title") or ""),
    )
    score = max(summary_score, title_score)
    left_topic = _primary_topic(left.get("tags") or [])
    right_topic = _primary_topic(right.get("tags") or [])
    if left_topic == right_topic and left_topic != "topic/general":
        score += 0.12
    return score


def _dedupe_principles(
    principles: list[dict],
    *,
    threshold: float = PRINCIPLE_DEDUP_THRESHOLD,
) -> list[dict]:
    """Keep higher-confidence principle; attach near-duplicates as related."""
    kept: list[dict] = []
    for item in principles:
        entry = {**item, "related": []}
        mate = None
        best = 0.0
        for k in kept:
            sim = _principle_affinity(item, k)
            if sim >= threshold and sim > best:
                mate = k
                best = sim
        if mate is not None:
            mate["related"].append(
                {
                    "rel": item["rel"],
                    "title": item["title"],
                    "confidence": item["confidence"],
                    "similarity": round(best, 2),
                }
            )
        else:
            kept.append(entry)
    return kept


def _primary_topic(tags: list[str]) -> str:
    topics = [t for t in tags if str(t).startswith("topic/")]
    if not topics:
        return "topic/general"
    order = {name: i for i, name in enumerate(TOPIC_GROUP_ORDER)}
    return sorted(topics, key=lambda t: (order.get(t, 999), t))[0]


def _format_principles_section(
    principles: list[dict],
    *,
    max_in_profile: int,
    json_rel: str,
    total_count: int,
) -> str:
    shown = principles[:max_in_profile]
    if not shown:
        return f"_No Level-2 pages with confidence ≥ {CONFIDENCE_FLOOR} yet._"

    groups: dict[str, list[dict]] = {}
    for item in shown:
        groups.setdefault(_primary_topic(item.get("tags") or []), []).append(item)

    def _group_key(name: str) -> tuple:
        try:
            idx = TOPIC_GROUP_ORDER.index(name)
        except ValueError:
            idx = 999
        max_conf = max(float(p.get("confidence", 0) or 0) for p in groups[name])
        return (idx, -max_conf, name)

    parts: list[str] = []
    for topic in sorted(groups.keys(), key=_group_key):
        parts.append(f"### {topic}")
        for item in groups[topic]:
            parts.append(_principle_line(item))
            for rel in item.get("related") or []:
                parts.append(
                    f"  - related: [[{rel['rel']}]] "
                    f"(conf {float(rel['confidence']):.2f}, sim {rel['similarity']:.2f})"
                )
        parts.append("")

    body = "\n".join(parts).rstrip()
    notes: list[str] = []
    hidden_related = sum(len(p.get("related") or []) for p in shown)
    if hidden_related:
        notes.append(
            f"_Near-duplicate principles folded under related "
            f"({hidden_related} suppressed from top-level; full index: `{json_rel}`)._"
        )
    if total_count > max_in_profile:
        notes.append(
            f"_Showing top {max_in_profile} of {total_count} after dedupe. "
            f"Full index: `{json_rel}`._"
        )
    if notes:
        body = body + "\n\n" + "\n".join(notes)
    return body


def _build_essence(
    principles: list[dict],
    *,
    coexistences: list[dict],
    tensions: list[str],
    hypotheses: list[dict],
) -> str:
    cores = [_rule_core(p.get("summary") or "") for p in principles[:4]]
    cores = [c for c in cores if c]
    if not cores:
        lead = "尚无可用 Level-2 原则快照。"
    else:
        lead = "核心原则：" + "；".join(cores[:3]) + "。"

    tension_bit = ""
    if coexistences:
        tension_bit = "最大张力：" + _truncate(
            coexistences[0].get("summary") or coexistences[0].get("title") or "",
            110,
        )
        if not tension_bit.endswith("。"):
            tension_bit += "。"
    elif tensions:
        tension_bit = "活跃矛盾：" + _truncate(tensions[0], 110)
        if not tension_bit.endswith("。"):
            tension_bit += "。"

    hyp_bit = ""
    if hypotheses:
        claim = _truncate(hypotheses[0].get("claim") or hypotheses[0].get("title") or "", 90)
        hyp_bit = f"已认账假设：{claim}"
        if not hyp_bit.endswith("。"):
            hyp_bit += "。"

    return " ".join(part for part in (lead, tension_bit, hyp_bit) if part)


def _collect_principles() -> list[dict]:
    items: list[dict] = []
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        meta = _parse_front_matter(content)
        if not _qualifies_principle(meta, content):
            continue
        conf = _confidence(meta) or 0.85
        items.append(
            {
                "title": str(meta.get("title") or path.stem),
                "path": path,
                "rel": _wiki_rel(path),
                "level": int(meta.get("level", 0) or 0),
                "confidence": conf,
                "summary": _summary_line(content),
                "tags": _tags_list(meta),
                "last_updated": str(meta.get("last_updated", "")),
            }
        )
    items.sort(key=_principle_sort_key)
    return items


def _collect_shifts(*, limit: int = 12) -> list[dict]:
    items: list[dict] = []
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        meta = _parse_front_matter(content)
        if "type/shift" not in " ".join(_tags_list(meta)):
            continue
        updated = str(meta.get("last_updated", ""))
        items.append(
            {
                "title": str(meta.get("title") or path.stem),
                "rel": _wiki_rel(path),
                "summary": _summary_line(content),
                "last_updated": updated,
            }
        )
    items.sort(key=lambda x: x["last_updated"], reverse=True)
    return items[:limit]


def _extract_evolution_section(content: str) -> str:
    m = re.search(r"## Evolution\s*\n(.*?)(?:\n## |\Z)", content, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _evolution_sort_key(date_str: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        return date_str
    if re.fullmatch(r"\d{4}", date_str):
        return f"{date_str}-01-01"
    return "0000-01-01"


def _evolution_signal_score(text: str) -> int:
    lower = text.lower()
    return sum(2 for term in EVOLUTION_SIGNAL_TERMS if term in lower)


def _is_evolution_noise(text: str) -> bool:
    return bool(EVOLUTION_NOISE_RE.search(text))


def _evolution_line_qualifies(*, body: str, is_shift: bool) -> bool:
    """Keep belief-change signal; drop ingest provenance noise."""
    if _is_evolution_noise(body):
        return False
    if is_shift:
        return True
    return _evolution_signal_score(body) > 0


def _collect_evolution(*, limit: int | None = None) -> list[dict]:
    limit = limit if limit is not None else twin_profile_max_evolution()
    entries: list[dict] = []

    for path in sorted(WIKI_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        section = _extract_evolution_section(content)
        if not section:
            continue

        meta = _parse_front_matter(content)
        tags_blob = " ".join(_tags_list(meta))
        level = int(meta.get("level", 0) or 0)
        is_shift = "type/shift" in tags_blob
        rel = _wiki_rel(path)
        title = str(meta.get("title") or path.stem)

        for line in section.splitlines():
            m = EVOLUTION_LINE_RE.match(line.strip())
            if not m:
                continue
            date_str, body = m.group(1), m.group(2).strip()
            if not body:
                continue
            if not _evolution_line_qualifies(body=body, is_shift=is_shift):
                continue

            signal = _evolution_signal_score(body)
            priority = signal
            if is_shift:
                priority += 10
            if level >= 2:
                priority += 5

            entries.append(
                {
                    "date": date_str,
                    "sort_date": _evolution_sort_key(date_str),
                    "rel": rel,
                    "title": title,
                    "text": body[:220] + ("…" if len(body) > 220 else ""),
                    "priority": priority,
                }
            )

    entries.sort(key=lambda x: (x["sort_date"], x["priority"]), reverse=True)
    return entries[:limit]


def _evolution_line(item: dict) -> str:
    return f"- {item['date']} — [[{item['rel']}]]: {item['text']}"


def _collect_tensions() -> list[str]:
    lines: list[str] = []
    contradict_re = re.compile(r"-\s*\*\*Contradicts\*\*:\s*(.+)", re.IGNORECASE)
    block_re = re.compile(
        r"<!-- BEGIN BACKLINKS -->(.*?)<!-- END BACKLINKS -->",
        re.DOTALL,
    )
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        block_match = block_re.search(content)
        if not block_match:
            continue
        for line in block_match.group(1).splitlines():
            match = contradict_re.match(line.strip())
            if not match:
                continue
            raw = HTML_COMMENT_RE.sub("", match.group(1)).strip()
            if not raw or raw.lower() in {"none", "none identified", "none."}:
                continue
            rel = _wiki_rel(path)
            lines.append(f"- [[{rel}]] → {raw}")
    return lines


def _has_coexistence_signal(text: str) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in COEXISTENCE_TERMS)


def _collect_coexistences(*, limit: int = 8) -> list[dict]:
    """Unresolved dual narratives from wiki openings with tension keywords."""
    items: list[dict] = []
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        meta = _parse_front_matter(content)
        summary = _summary_line(content)
        if not summary or not _has_coexistence_signal(summary):
            continue
        is_shift = "type/shift" in _tags_list(meta)
        items.append(
            {
                "rel": _wiki_rel(path),
                "title": str(meta.get("title") or path.stem),
                "summary": summary,
                "last_updated": str(meta.get("last_updated", "")),
                "is_shift": is_shift,
            }
        )
    items.sort(key=lambda x: (x["is_shift"], x["last_updated"]), reverse=True)
    return items[:limit]


def _parse_hypothesis_blocks(text: str) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    field: str | None = None
    buf: list[str] = []

    def _flush_field() -> None:
        nonlocal field, buf
        if current is None or field is None:
            buf = []
            field = None
            return
        value = "\n".join(buf).strip()
        current[field] = value
        buf = []
        field = None

    def _flush_block() -> None:
        nonlocal current
        _flush_field()
        if current:
            blocks.append(current)
        current = None

    for raw_line in text.splitlines():
        heading = HYPOTHESIS_HEADING_RE.match(raw_line.strip())
        if heading:
            _flush_block()
            current = {
                "id": heading.group(1),
                "title": heading.group(2).strip(),
                "status": "",
                "confidence": "",
                "category": "",
                "claim": "",
                "judgment": "",
                "notes": "",
            }
            continue
        if current is None:
            continue
        stripped = raw_line.strip()
        if stripped.startswith("Status:"):
            _flush_field()
            current["status"] = stripped.split(":", 1)[1].strip().lower()
            continue
        if stripped.startswith("Confidence:"):
            _flush_field()
            current["confidence"] = stripped.split(":", 1)[1].strip().lower()
            continue
        if stripped.startswith("Category:"):
            _flush_field()
            current["category"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped in {"Claim:", "User Judgment:", "Notes:", "Evidence:", "Open Questions:", "Evolution:"}:
            _flush_field()
            label = stripped[:-1].lower()
            if label == "user judgment":
                field = "judgment"
            elif label == "claim":
                field = "claim"
            elif label == "notes":
                field = "notes"
            else:
                field = None  # skip Evidence / Open Questions / Evolution bodies
            buf = []
            continue
        if field:
            buf.append(raw_line)

    _flush_block()
    return blocks


def _hypothesis_included(item: dict) -> bool:
    status = (item.get("status") or "").strip().lower()
    judgment = (item.get("judgment") or "").strip().lower()
    if status in HYPOTHESIS_EXCLUDE or judgment in HYPOTHESIS_EXCLUDE:
        return False
    if status in HYPOTHESIS_INCLUDE_STATUSES:
        return True
    if judgment in HYPOTHESIS_INCLUDE_JUDGMENTS:
        return True
    return False


def _collect_judged_hypotheses(
    *, path: Path | None = None, limit: int = 12
) -> list[dict]:
    hyp_path = path or TWIN_SELF_HYPOTHESES
    if not hyp_path.exists():
        return []
    try:
        text = hyp_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    items = [h for h in _parse_hypothesis_blocks(text) if _hypothesis_included(h)]
    items.sort(key=lambda h: (h.get("judgment") != "revised", h.get("id", "")))
    return items[:limit]


def _truncate(text: str, max_len: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


def _hypothesis_line(item: dict) -> str:
    hyp_rel = workspace_relpath(TWIN_SELF_HYPOTHESES)
    status = item.get("status") or "?"
    judgment = item.get("judgment") or "?"
    claim = _truncate(item.get("claim") or item.get("title") or "")
    notes = (item.get("notes") or "").strip()
    note_bit = ""
    if notes and notes.lower() not in {"none", "none.", "n/a"}:
        note_bit = f" — note: {_truncate(notes, 120)}"
    return (
        f"- [[{hyp_rel}#{item['id']}]] ({status}/{judgment}) — {claim}{note_bit}"
    )


def _coexistence_line(item: dict) -> str:
    return f"- [[{item['rel']}]] — {item['summary']}"


def _format_tensions_block(
    contradicts: list[str], coexistences: list[dict]
) -> str:
    parts: list[str] = ["### Contradicts"]
    if contradicts:
        parts.extend(contradicts)
    else:
        parts.append("_No Contradicts edges in wiki backlinks yet._")
    parts.append("")
    parts.append("### Unresolved coexistences")
    parts.append(
        "_Deterministic heuristic from tension-marked wiki openings; label as "
        "[AI Synthesis] until you confirm or add Contradicts._"
    )
    if coexistences:
        parts.extend(_coexistence_line(c) for c in coexistences)
    else:
        parts.append("_None detected._")
    return "\n".join(parts)


def _principle_line(item: dict) -> str:
    conf = item["confidence"]
    summary = item["summary"] or item["title"]
    return f"- [[{item['rel']}]] (L{item['level']}, conf {conf:.2f}) — {summary}"


def _write_principles_json(principles: list[dict], *, built_at: datetime) -> None:
    payload = {
        "compiled_at": built_at.isoformat(timespec="seconds"),
        "principle_count": len(principles),
        "confidence_floor": CONFIDENCE_FLOOR,
        "level_min": 2,
        "principles": [
            {
                "title": p["title"],
                "rel": p["rel"],
                "level": p["level"],
                "confidence": p["confidence"],
                "summary": p["summary"],
                "last_updated": p["last_updated"],
                "tags": p["tags"],
            }
            for p in principles
        ],
    }
    TWIN_PRINCIPLES_JSON.parent.mkdir(parents=True, exist_ok=True)
    TWIN_PRINCIPLES_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_profile_markdown(*, built_at: datetime | None = None) -> str:
    built_at = built_at or datetime.now()
    stamp = built_at.isoformat(timespec="seconds")
    date_str = built_at.strftime("%Y-%m-%d")
    max_in_profile = twin_profile_max_principles()

    principles = _collect_principles()
    deduped = _dedupe_principles(principles)
    shifts = _collect_shifts()
    tensions = _collect_tensions()
    coexistences = _collect_coexistences()
    hypotheses = _collect_judged_hypotheses()
    evolution = _collect_evolution()

    shift_lines = [
        f"- [[{s['rel']}]] — {s['summary'] or s['title']}" for s in shifts
    ]
    evolution_lines = [_evolution_line(item) for item in evolution]
    hypothesis_lines = [_hypothesis_line(h) for h in hypotheses]
    tension_block = _format_tensions_block(tensions, coexistences)

    hyp_rel = workspace_relpath(TWIN_SELF_HYPOTHESES)
    json_rel = workspace_relpath(TWIN_PRINCIPLES_JSON)
    essence = _build_essence(
        deduped,
        coexistences=coexistences,
        tensions=tensions,
        hypotheses=hypotheses,
    )
    principle_block = _format_principles_section(
        deduped,
        max_in_profile=max_in_profile,
        json_rel=json_rel,
        total_count=len(deduped),
    )
    related_suppressed = sum(len(p.get("related") or []) for p in deduped)

    if hypothesis_lines:
        hypothesis_block = "\n".join(hypothesis_lines)
    else:
        hypothesis_block = (
            f"_No supported/revised entries in `{hyp_rel}` yet "
            f"(rejected excluded)._"
        )

    return f"""---
title: Digital Twin Profile
last_updated: {stamp}
description: Compact snapshot of Level-2 principles (internal twin; rbrain chat = later).
level: 2
tags: [type/principle, twin/profile]
compiled_at: {stamp}
principle_count: {len(principles)}
principle_count_shown: {min(len(deduped), max_in_profile)}
principle_deduped: {len(deduped)}
related_suppressed: {related_suppressed}
hypothesis_count: {len(hypotheses)}
coexistence_count: {len(coexistences)}
principles_index: {json_rel}
---

> {essence}

## Operating principles

{principle_block}

## Judged hypotheses

_User-judged claims from `{hyp_rel}` (supported status or revised/accepted judgment)._

{hypothesis_block}

## Active tensions

{tension_block}

## Recent shifts

{chr(10).join(shift_lines) if shift_lines else "_No pages tagged type/shift yet._"}

## Recent evolution

{chr(10).join(evolution_lines) if evolution_lines else "_No high-signal ## Evolution entries yet (type/shift or belief-change lines; Distilled-from provenance excluded)._"}

## Compiled

- {date_str}: Regenerated from `self-wiki/wiki/` via ingest (`make sync` / `python scripts/cli.py twin`).
- Catalog: `{json_rel}` — {len(principles)} principles, {len(deduped)} after near-dup fold ({related_suppressed} related), {len(hypotheses)} judged hypotheses, {len(tensions)} Contradicts, {len(coexistences)} coexistences, {len(evolution)} evolution, {len(shifts)} shifts.
- Query runtime reads `{json_rel}` with query-aware selection in `prepare_query` (deterministic, not LLM-generated).
"""


def build_twin_profile(*, write: bool = True) -> Path:
    TWIN_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now()
    principles = _collect_principles()
    text = build_profile_markdown(built_at=built_at)
    if write:
        TWIN_PRINCIPLES_JSON.parent.mkdir(parents=True, exist_ok=True)
        _write_principles_json(principles, built_at=built_at)
        TWIN_PROFILE.write_text(text, encoding="utf-8")
        logger.info(
            "Wrote twin profile to %s (%d principles shown, %d in index)",
            TWIN_PROFILE.relative_to(WORKSPACE_PATH),
            min(len(principles), twin_profile_max_principles()),
            len(principles),
        )
    return TWIN_PROFILE


# --- Twin context for query/lint (merged from twin_context.py) ---


def load_principles() -> list[dict]:
    if TWIN_PRINCIPLES_JSON.exists():
        try:
            data = json.loads(TWIN_PRINCIPLES_JSON.read_text(encoding="utf-8"))
            items = data.get("principles", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                return items
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _normalize_terms(terms: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in terms:
        t = t.strip().lower()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def score_principle(item: dict, query: str, query_terms: list[str]) -> int:
    blob = " ".join(
        [
            str(item.get("title", "")),
            str(item.get("summary", "")),
            str(item.get("rel", "")),
            query,
        ]
    ).lower()
    score = 0
    for term in _normalize_terms(query_terms):
        if term in blob:
            score += 3
    try:
        score += int(float(item.get("level", 0) or 0))
    except (TypeError, ValueError):
        pass
    try:
        score += int(float(item.get("confidence", 0) or 0) * 2)
    except (TypeError, ValueError):
        pass
    return score


def _extract_profile_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current and lines:
                sections[current] = "\n".join(lines).strip()
            heading = line[3:].strip().lower()
            if heading.startswith("active tensions"):
                current = "tensions"
            elif heading.startswith("judged hypotheses"):
                current = "hypotheses"
            elif heading.startswith("recent shifts"):
                current = "shifts"
            elif heading.startswith("recent evolution"):
                current = "evolution"
            else:
                current = None
            lines = []
            continue
        if current:
            lines.append(line)
    if current and lines:
        sections[current] = "\n".join(lines).strip()
    return sections


def _format_principle_line(item: dict) -> str:
    conf = float(item.get("confidence", 0) or 0)
    level = int(item.get("level", 0) or 0)
    summary = str(item.get("summary") or item.get("title", ""))
    rel = str(item.get("rel", ""))
    return f"- [[{rel}]] (L{level}, conf {conf:.2f}) — {summary}"


def profile_excerpt_for_query(
    query: str,
    query_terms: list[str],
    *,
    max_chars: int | None = None,
    top_k: int | None = None,
) -> str:
    from config import twin_profile_excerpt_chars, twin_query_principles_k

    max_chars = max_chars if max_chars is not None else twin_profile_excerpt_chars()
    top_k = top_k if top_k is not None else twin_query_principles_k()

    principles = load_principles()
    profile_rel = workspace_relpath(TWIN_PROFILE)
    if not principles and not TWIN_PROFILE.exists():
        return f"_{profile_rel} not built yet — run make sync or python scripts/cli.py twin._"

    ranked = sorted(
        principles,
        key=lambda p: (
            -score_principle(p, query, query_terms),
            -int(p.get("level", 0) or 0),
            -float(p.get("confidence", 0) or 0),
        ),
    )
    selected = ranked[:top_k] if ranked else []

    json_rel = workspace_relpath(TWIN_PRINCIPLES_JSON)
    parts = [
        f"> Query-relevant twin context (deterministic; from {json_rel}).",
        "",
        "## Relevant operating principles",
    ]
    if selected:
        parts.extend(_format_principle_line(p) for p in selected)
    else:
        parts.append("_No principles.json — rebuild with `python scripts/cli.py twin`._")

    if TWIN_PROFILE.exists():
        sections = _extract_profile_sections(
            TWIN_PROFILE.read_text(encoding="utf-8", errors="ignore")
        )
        if sections.get("hypotheses"):
            parts.extend(["", "## Judged hypotheses", sections["hypotheses"]])
        if sections.get("tensions"):
            parts.extend(["", "## Active tensions", sections["tensions"]])
        if sections.get("shifts"):
            parts.extend(["", "## Recent shifts", sections["shifts"]])
        if sections.get("evolution"):
            parts.extend(["", "## Recent evolution", sections["evolution"]])

    text = "\n".join(parts)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n… [twin context truncated]"


def lint_principle_excerpts(*, max_pages: int = 15) -> list[str]:
    principles = load_principles()
    if not principles:
        return []

    ranked = sorted(
        principles,
        key=lambda p: (
            -int(p.get("level", 0) or 0),
            -float(p.get("confidence", 0) or 0),
            str(p.get("last_updated", "")),
        ),
    )

    excerpts: list[str] = []
    for item in ranked[:max_pages]:
        rel = str(item.get("rel", ""))
        summary = str(item.get("summary") or item.get("title", ""))
        excerpts.append(f"### [[{rel}]]\n> {summary}\n")
    return excerpts


def lint_profile_summary(*, max_chars: int = 2000) -> str:
    profile_rel = workspace_relpath(TWIN_PROFILE)
    if not TWIN_PROFILE.exists():
        return f"_{profile_rel} not built — run make sync or python scripts/cli.py twin._"

    text = TWIN_PROFILE.read_text(encoding="utf-8", errors="ignore")
    principles = load_principles()
    header_end = text.find("## Operating principles")
    header = text[:header_end].strip() if header_end > 0 else text[:800]

    sections = _extract_profile_sections(text)
    parts = [header, "", "## Operating principles"]
    if principles:
        cap = min(15, len(principles))
        ranked = sorted(
            principles,
            key=lambda p: (
                -int(p.get("level", 0) or 0),
                -float(p.get("confidence", 0) or 0),
            ),
        )
        parts.extend(_format_principle_line(p) for p in ranked[:cap])
        total = len(principles)
        if total > cap:
            rel_json = workspace_relpath(TWIN_PRINCIPLES_JSON)
            parts.append(f"\n_… and {total - cap} more in `{rel_json}`._")
    if sections.get("tensions"):
        parts.extend(["", "## Active tensions", sections["tensions"]])
    if sections.get("shifts"):
        parts.extend(["", "## Recent shifts", sections["shifts"]])
    if sections.get("evolution"):
        parts.extend(["", "## Recent evolution", sections["evolution"]])

    out = "\n".join(parts)
    if len(out) <= max_chars:
        return out
    return out[:max_chars] + "\n… [PROFILE summary truncated]"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_twin_profile()
