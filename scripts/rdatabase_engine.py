"""rdatabase pipeline: ensure index → prepare → run-skill(rdatabase) → save."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from config import RDATABASE_OUTPUTS_DIR, WORKSPACE_PATH, workspace_relpath
from llm_provider import model_name, provider_for_role
from log_utils import append_log
from pending_cleanup import cleanup_pending_artifacts
from prepare_rdatabase import prepare_rdatabase
from rdatabase_index import ensure_index
from rdatabase_retrieval import print_retrieval_debug
from run_skill import run_skill_from_pending

logger = logging.getLogger(__name__)


def sanitize_filename(question: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", question).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return safe[:max_len] or "rdatabase"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def save_output(question: str, answer: str, candidates: list[dict[str, Any]]) -> Path:
    RDATABASE_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    last_updated = now.isoformat(timespec="seconds")
    safe_q = sanitize_filename(question)
    out = RDATABASE_OUTPUTS_DIR / f"{safe_q}-{date_str}.md"

    sources_md = "\n".join(
        f"- [[{c['path']}]] · #p{c['para']} · L{c['start_line']}–L{c['end_line']} "
        f"(score={c.get('score')}, kind={c.get('kind')})"
        for c in candidates
    ) or "- (none)"

    note = f"""---
last_updated: {last_updated}
title: {yaml_string(question)}
description: {yaml_string(f"rdatabase raw-only Q&A for: {question}")}
level: 0
tags: [type/synthesis, rdatabase]
date: {date_str}
question: {yaml_string(question)}
scope: self-wiki/raw
---

> Raw-only proprietary-facts snapshot. Claims are valid only with verbatim cites from `raw/`. Not a wiki principle page.

## Question

{question}

## Answer

{answer}

## Retrieval candidates

{sources_md}

## Evolution

- {date_str}: Created by `rdatabase` from keyword-ranked `raw/` paragraphs.
"""
    out.write_text(note, encoding="utf-8")
    return out


def run_rdatabase(
    query: str,
    *,
    provider: str | None = None,
    debug_retrieval: bool = False,
    save: bool = True,
    force_index: bool = False,
) -> dict[str, Any]:
    llm_provider = provider_for_role("rdatabase", provider)
    index = ensure_index(force=force_index)
    pending, pending_path = prepare_rdatabase(query, index=index, provider=llm_provider)

    if debug_retrieval:
        print_retrieval_debug(
            {
                "language": pending["language"],
                "query_terms": pending["query_terms"],
                "candidates": pending["candidates"],
                "evidence_tokens": pending.get("evidence_tokens"),
                "index_paragraph_count": index.get("paragraph_count"),
                "index_built_at": index.get("built_at"),
            }
        )

    logger.info(
        "rdatabase LLM: provider=%s model=%s",
        llm_provider,
        model_name(llm_provider, role="rdatabase"),
    )
    result = run_skill_from_pending(pending_path, provider=llm_provider, write_output=True)
    answer = result["text"]
    cleanup_pending_artifacts(pending_path)

    out: dict[str, Any] = {
        "query": query,
        "answer": answer,
        "provider": llm_provider,
        "model": model_name(llm_provider, role="rdatabase"),
        "language": pending["language"],
        "query_terms": pending["query_terms"],
        "candidates": pending["candidates"],
        "sources": [
            {
                "id": c["id"],
                "path": c["path"],
                "file": c["file"],
                "lines": [c["start_line"], c["end_line"]],
                "kind": c.get("kind"),
                "score": c.get("score"),
                "source_url": c.get("source_url"),
            }
            for c in pending["candidates"]
        ],
    }
    if save:
        path = save_output(query, answer, pending["candidates"])
        out["output_path"] = workspace_relpath(path)
        logger.info("Saved rdatabase output to %s", path)

    n_cand = len(pending.get("candidates") or [])
    q_short = query.replace("\n", " ").strip()
    if len(q_short) > 72:
        q_short = q_short[:69] + "…"
    out_rel = out.get("output_path")
    if out_rel:
        append_log(
            "rdatabase",
            f"created output | {q_short} | candidates={n_cand} | {out_rel}",
        )
    else:
        append_log(
            "rdatabase",
            f"ran (no-save) | {q_short} | candidates={n_cand}",
        )
    return out
