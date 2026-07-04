"""Suggest promote commands after query answers (Karpathy compounding loop)."""

from __future__ import annotations

import re
from typing import Iterable


COGNITIVE_SHIFT = re.compile(r"\[Cognitive Shift\]", re.IGNORECASE)
SOCRATIC_OBS = re.compile(r"\[Socratic Observation\]", re.IGNORECASE)


def _top_wiki_target(candidates: Iterable[dict]) -> str | None:
    best_title: str | None = None
    best_score = -1.0
    for item in candidates:
        title = (item.get("title") or item.get("path") or "").strip()
        if not title:
            continue
        score = float(item.get("score") or item.get("relevance") or 0)
        if score > best_score:
            best_score = score
            best_title = title.split("/")[-1].replace(".md", "") if "/" in title else title
    return best_title


def should_suggest_promote(answer: str) -> bool:
    return bool(COGNITIVE_SHIFT.search(answer) or SOCRATIC_OBS.search(answer))


def format_promote_suggestion(
    *,
    answer: str,
    output_path: str | None,
    candidates: list[dict] | None = None,
    query: str | None = None,
) -> str | None:
    if not should_suggest_promote(answer):
        return None
    if not output_path:
        return None

    target = _top_wiki_target(candidates or [])
    if not target:
        target = "<wiki-page-title>"

    lines = [
        "",
        "---",
        "Promote suggestion (query → wiki compounding):",
        f'  make promote FILE="{output_path}" TARGET="{target}" CONFIRM=1',
    ]
    if query:
        lines.append(f"  # query: {query[:80]}")
    lines.append("---")
    return "\n".join(lines)
