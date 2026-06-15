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
    WIKI_DIR,
    WORKSPACE_PATH,
    twin_profile_max_evolution,
    twin_profile_max_principles,
)

logger = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.7
EVOLUTION_LINE_RE = re.compile(r"^-\s*(\d{4}(?:-\d{2}-\d{2})?)\s*:\s*(.+?)\s*$")
EVOLUTION_SIGNAL_TERMS = (
    "promoted",
    "cognitive shift",
    "shift",
    "revised",
    "contradict",
    "migrat",
    "转化",
    "转变",
    "认知",
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


def _grounded_in_apple_notes(content: str) -> bool:
    """P1 twin filter: only principles traced to origin-apple-notes raw sources."""
    return "raw/origin-apple-notes" in content


def _qualifies_principle(meta: dict, content: str = "") -> bool:
    level = int(meta.get("level", 0) or 0)
    confidence = _confidence(meta)
    if confidence <= 0 and level >= 2:
        confidence = 0.85
    if level < 2:
        return False
    if content and not _grounded_in_apple_notes(content):
        return False
    return confidence >= CONFIDENCE_FLOOR


def _principle_sort_key(item: dict) -> tuple:
    return (
        -int(item.get("level", 0) or 0),
        -float(item.get("confidence", 0) or 0),
        str(item.get("last_updated", "")),
    )


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

            signal = _evolution_signal_score(body)
            qualifies = is_shift or level >= 2 or signal > 0
            if not qualifies:
                continue

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
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        m = re.search(
            r"## Backlinks\s*\n.*?-\s*\*\*Contradicts\*\*:\s*(.+?)(?:\n-|\n## |\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if not m:
            continue
        raw = m.group(1).strip()
        if not raw or raw.lower() in {"none", "none identified", "none."}:
            continue
        rel = _wiki_rel(path)
        lines.append(f"- [[{rel}]] → {raw}")
    return lines


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
    shifts = _collect_shifts()
    tensions = _collect_tensions()
    evolution = _collect_evolution()
    profile_principles = principles[:max_in_profile]

    principle_lines = [_principle_line(item) for item in profile_principles]
    shift_lines = [
        f"- [[{s['rel']}]] — {s['summary'] or s['title']}" for s in shifts
    ]
    evolution_lines = [_evolution_line(item) for item in evolution]

    tension_block = (
        "\n".join(tensions) if tensions else "_No Contradicts edges in wiki backlinks yet._"
    )

    try:
        json_rel = str(TWIN_PRINCIPLES_JSON.relative_to(WORKSPACE_PATH))
    except ValueError:
        json_rel = "twin/principles.json"
    snapshot = (
        f"Top {len(profile_principles)} of {len(principles)} Level-2 principle(s) "
        f"(confidence ≥ {CONFIDENCE_FLOOR}), {len(evolution)} recent evolution entry(ies), "
        f"{len(shifts)} recent shift(s), {len(tensions)} tension edge(s). "
        f"Full catalog: `{json_rel}`."
    )

    overflow_note = ""
    if len(principles) > max_in_profile:
        overflow_note = (
            f"\n\n_Showing top {max_in_profile} by level, confidence, and recency. "
            f"Full index ({len(principles)} entries): `{json_rel}`._"
        )

    return f"""---
title: Digital Twin Profile
last_updated: {stamp}
description: Compact snapshot of Level-2 principles (internal twin, not public Reid AI).
level: 2
tags: [type/principle, twin/profile]
compiled_at: {stamp}
principle_count: {len(principles)}
principle_count_shown: {len(profile_principles)}
principles_index: {json_rel}
---

> {snapshot} Built by `build_twin_profile.py` after post-ingest (backliner → index → twin).

## Operating principles

{chr(10).join(principle_lines) if principle_lines else f"_No Level-2 pages with confidence ≥ {CONFIDENCE_FLOOR} yet._"}{overflow_note}

## Active tensions

{tension_block}

## Recent shifts

{chr(10).join(shift_lines) if shift_lines else "_No pages tagged type/shift yet._"}

## Recent evolution

{chr(10).join(evolution_lines) if evolution_lines else "_No qualifying ## Evolution entries yet (Level-2, type/shift, or high-signal lines)._"}

## Compiled

- {date_str}: Regenerated from `self-wiki/wiki/` via post-ingest (`make sync` / `python scripts/cli.py twin`).
- Query runtime reads `twin/principles.json` with query-aware selection in `prepare_query` (deterministic, not LLM-generated).
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
    if not principles and not TWIN_PROFILE.exists():
        return "_twin/PROFILE.md not built yet — run make sync or python scripts/cli.py twin._"

    ranked = sorted(
        principles,
        key=lambda p: (
            -score_principle(p, query, query_terms),
            -int(p.get("level", 0) or 0),
            -float(p.get("confidence", 0) or 0),
        ),
    )
    selected = ranked[:top_k] if ranked else []

    parts = [
        "> Query-relevant twin context (deterministic; from twin/principles.json).",
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
    if not TWIN_PROFILE.exists():
        return "_twin/PROFILE.md not built — run make sync or python scripts/cli.py twin._"

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
            try:
                rel_json = str(TWIN_PRINCIPLES_JSON.relative_to(WORKSPACE_PATH))
            except ValueError:
                rel_json = "twin/principles.json"
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
