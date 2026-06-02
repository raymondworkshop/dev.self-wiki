"""Deterministic digital twin snapshot from Level-2 / principle wiki pages."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from config import TWIN_PROFILE, WIKI_DIR, WORKSPACE_PATH

logger = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.7


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


def _qualifies_principle(meta: dict) -> bool:
    level = int(meta.get("level", 0) or 0)
    tags = _tags_list(meta)
    tag_blob = " ".join(tags)
    confidence = _confidence(meta)
    if confidence <= 0 and level >= 2:
        confidence = 0.85
    if confidence < CONFIDENCE_FLOOR:
        return False
    return level >= 2 or "type/principle" in tag_blob


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
        if not _qualifies_principle(meta):
            continue
        items.append(
            {
                "title": str(meta.get("title") or path.stem),
                "path": path,
                "rel": _wiki_rel(path),
                "level": int(meta.get("level", 0) or 0),
                "confidence": _confidence(meta) or 0.85,
                "summary": _summary_line(content),
                "tags": _tags_list(meta),
            }
        )
    items.sort(key=lambda x: (-x["level"], -x["confidence"], x["title"].lower()))
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


def build_profile_markdown(*, built_at: datetime | None = None) -> str:
    built_at = built_at or datetime.now()
    stamp = built_at.isoformat(timespec="seconds")
    date_str = built_at.strftime("%Y-%m-%d")

    principles = _collect_principles()
    shifts = _collect_shifts()
    tensions = _collect_tensions()

    principle_lines = []
    for item in principles:
        conf = item["confidence"]
        summary = item["summary"] or item["title"]
        principle_lines.append(
            f"- [[{item['rel']}]] (L{item['level']}, conf {conf:.2f}) — {summary}"
        )

    shift_lines = [
        f"- [[{s['rel']}]] — {s['summary'] or s['title']}" for s in shifts
    ]

    tension_block = "\n".join(tensions) if tensions else "_No Contradicts edges in wiki backlinks yet._"

    snapshot = (
        f"Aggregated {len(principles)} principle page(s), "
        f"{len(shifts)} recent shift(s), {len(tensions)} tension edge(s)."
    )

    return f"""---
title: Digital Twin Profile
last_updated: {stamp}
description: Deterministic snapshot of Level-2 and high-confidence principles (internal twin, not public Reid AI).
level: 2
tags: [type/principle, twin/profile]
compiled_at: {stamp}
principle_count: {len(principles)}
---

> {snapshot} Built by `build_twin_profile.py` after post-ingest (backliner → index → twin).

## Operating principles

{chr(10).join(principle_lines) if principle_lines else f"_No Level-2 / type/principle pages with confidence ≥ {CONFIDENCE_FLOOR} yet._"}

## Active tensions

{tension_block}

## Recent shifts

{chr(10).join(shift_lines) if shift_lines else "_No pages tagged type/shift yet._"}

## Compiled

- {date_str}: Regenerated from `self-wiki/wiki/` via post-ingest (`make sync` / `make post-ingest`).
- Query runtime reads this file in `prepare_query` as twin context (deterministic, not LLM-generated).
"""


def build_twin_profile(*, write: bool = True) -> Path:
    TWIN_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    text = build_profile_markdown()
    if write:
        TWIN_PROFILE.write_text(text, encoding="utf-8")
        logger.info("Wrote twin profile to %s", TWIN_PROFILE.relative_to(WORKSPACE_PATH))
    return TWIN_PROFILE


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_twin_profile()
