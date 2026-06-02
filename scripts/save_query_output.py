"""Save query answers to self-wiki/outputs as Level-1 synthesis notes."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from config import OUTPUTS_DIR, WORKSPACE_PATH


def sanitize_filename(question: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", question).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return safe[:max_len] or "query"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def save_output(question: str, messages: List[Dict[str, str]]) -> Path:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    last_updated = now.isoformat(timespec="seconds")
    safe_q = sanitize_filename(question)
    out = OUTPUTS_DIR / f"{safe_q}-{date_str}.md"

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
