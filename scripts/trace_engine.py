"""trace pipeline: ensure index → prepare → run-skill(trace) → save."""

from __future__ import annotations

import json
import logging
import os
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from config import TRACE_OUTPUTS_DIR, WORKSPACE_PATH, workspace_relpath
from llm_provider import model_name, provider_for_role
from log_utils import append_log
from pending_cleanup import cleanup_pending_artifacts
from prepare_trace import prepare_trace
from trace_index import ensure_index, ephemeral_index_from_upload, get_paragraph
from trace_retrieval import print_retrieval_debug
from run_skill import run_skill_from_pending

logger = logging.getLogger(__name__)

_ALLOWED_TRACE_MODELS = frozenset({"mlx", "gpt", "ultra", "cloud"})


@contextmanager
def _trace_model_override(model: str | None) -> Iterator[None]:
    """Temporarily set TRACE_LLM_MODEL for one ask (gateway alias: mlx|gpt|ultra|cloud)."""
    if not model:
        yield
        return
    key = "TRACE_LLM_MODEL"
    previous = os.environ.get(key)
    os.environ[key] = model
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def normalize_trace_model(raw: str | None) -> str | None:
    if not raw:
        return None
    value = str(raw).strip().lower()
    if value in _ALLOWED_TRACE_MODELS:
        return value
    return None

# [[raw/…]] · #p12  or  raw/…#p12
_CITE_WIKILINK_RE = re.compile(
    r"\[\[(?P<path>raw/[^\]|#]+?)\]\]\s*·\s*#p(?P<para>\d+)",
    re.IGNORECASE,
)
_CITE_ID_RE = re.compile(
    r"(?P<path>raw/[^\s\]|#]+?)#p(?P<para>\d+)",
    re.IGNORECASE,
)
_PROVENANCE_SECTION_RE = re.compile(
    r"(?ms)^##[ \t]*Provenance\b.*?(?=^##[ \t]+\S|\Z)",
)


def sanitize_filename(question: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", question).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return safe[:max_len] or "trace"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def extract_cited_para_ids(answer: str) -> list[str]:
    """Ordered unique paragraph ids referenced in the model answer."""
    found: list[str] = []
    seen: set[str] = set()
    for cre in (_CITE_WIKILINK_RE, _CITE_ID_RE):
        for m in cre.finditer(answer or ""):
            path = m.group("path").strip()
            para = m.group("para")
            pid = f"{path}#p{para}"
            if pid not in seen:
                seen.add(pid)
                found.append(pid)
    return found


def _blockquote(text: str) -> str:
    lines = (text or "").splitlines() or [""]
    return "\n".join(f"> {line}" for line in lines)


def resolve_paragraph(
    para_id: str,
    *,
    index: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for c in candidates:
        if c.get("id") == para_id:
            return c
    return get_paragraph(para_id, index)


def format_provenance_entry(para: dict[str, Any], *, note: str | None = None) -> str:
    path = para.get("path") or ""
    pnum = para.get("para")
    if pnum is None and para.get("id"):
        tail = str(para["id"]).rsplit("#p", 1)[-1]
        pnum = tail if tail.isdigit() else "?"
    start = para.get("start_line")
    end = para.get("end_line")
    header = f"- [[{path}]] · #p{pnum} · L{start}–L{end}"
    body = _blockquote(para.get("text") or "")
    if note:
        return f"{header}\n{body}\n  — {note}"
    return f"{header}\n{body}"


def build_full_provenance_md(
    para_ids: list[str],
    *,
    index: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
) -> str:
    blocks: list[str] = []
    for pid in para_ids:
        para = resolve_paragraph(pid, index=index, candidates=candidates)
        if not para:
            blocks.append(f"- `{pid}`\n> (paragraph not found in index)")
            continue
        blocks.append(format_provenance_entry(para))
    return "\n\n".join(blocks) if blocks else "- (none)"


def strip_provenance_section(answer: str) -> str:
    text = answer or ""
    return _PROVENANCE_SECTION_RE.sub("", text).rstrip()


def enforce_full_provenance(
    answer: str,
    *,
    index: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
) -> str:
    """Replace ## Provenance with full text for cited ids + every pack candidate."""
    cited = extract_cited_para_ids(answer)
    cited_set = set(cited)
    # Always surface the whole Evidence Pack, not only what the model happened to cite.
    pack_ids = [c["id"] for c in candidates if c.get("id")]
    ordered: list[str] = []
    for pid in cited:
        if pid not in ordered:
            ordered.append(pid)
    for pid in pack_ids:
        if pid not in cited_set and pid not in ordered:
            ordered.append(pid)
    if not ordered:
        ordered = pack_ids

    blocks: list[str] = []
    for pid in ordered:
        para = resolve_paragraph(pid, index=index, candidates=candidates)
        if not para:
            blocks.append(f"- `{pid}`\n> (paragraph not found in index)")
            continue
        note = None if pid in cited_set else "Evidence Pack hit (not cited in Answer)"
        blocks.append(format_provenance_entry(para, note=note))
    provenance = "\n\n".join(blocks) if blocks else "- (none)"
    body = strip_provenance_section(answer)
    return f"{body}\n\n## Provenance\n\n{provenance}\n"


def save_output(
    question: str,
    answer: str,
    candidates: list[dict[str, Any]],
    *,
    scope: str | None = None,
) -> Path:
    TRACE_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    last_updated = now.isoformat(timespec="seconds")
    safe_q = sanitize_filename(question)
    out = TRACE_OUTPUTS_DIR / f"{safe_q}-{date_str}.md"

    sources_md = "\n".join(
        f"- [[{c['path']}]] · #p{c['para']} · L{c['start_line']}–L{c['end_line']} "
        f"(score={c.get('score')}, kind={c.get('kind')})"
        for c in candidates
    ) or "- (none)"
    scope_yaml = yaml_string(scope) if scope else '"self-wiki/raw"'

    note = f"""---
last_updated: {last_updated}
title: {yaml_string(question)}
description: {yaml_string(f"trace raw-only Q&A for: {question}")}
level: 0
tags: [type/synthesis, trace]
date: {date_str}
question: {yaml_string(question)}
scope: {scope_yaml}
---

> Raw-only proprietary-facts snapshot. Claims are valid only with verbatim cites from `raw/`. Not a wiki principle page.

## Question

{question}

## Answer

{answer}

## Retrieval candidates

{sources_md}

## Evolution

- {date_str}: Created by `trace` from keyword-ranked `raw/` paragraphs.
"""
    out.write_text(note, encoding="utf-8")
    return out


def run_trace(
    query: str,
    *,
    provider: str | None = None,
    debug_retrieval: bool = False,
    save: bool = True,
    force_index: bool = False,
    scope: str | None = None,
    model: str | None = None,
    upload_text: str | None = None,
    upload_filename: str | None = None,
) -> dict[str, Any]:
    chosen = normalize_trace_model(model)
    with _trace_model_override(chosen):
        return _run_trace_body(
            query,
            provider=provider,
            debug_retrieval=debug_retrieval,
            save=save,
            force_index=force_index,
            scope=scope,
            upload_text=upload_text,
            upload_filename=upload_filename,
        )


def _run_trace_body(
    query: str,
    *,
    provider: str | None = None,
    debug_retrieval: bool = False,
    save: bool = True,
    force_index: bool = False,
    scope: str | None = None,
    upload_text: str | None = None,
    upload_filename: str | None = None,
) -> dict[str, Any]:
    llm_provider = provider_for_role("trace", provider)
    if upload_text is not None and str(upload_text).strip():
        index = ephemeral_index_from_upload(
            str(upload_text), filename=upload_filename
        )
        scope = index.get("upload_path") or scope
    else:
        index = ensure_index(force=force_index)
    pending, pending_path = prepare_trace(
        query, index=index, provider=llm_provider, scope=scope
    )

    if debug_retrieval:
        print_retrieval_debug(
            {
                "language": pending["language"],
                "scope": pending.get("scope"),
                "scope_paths": pending.get("scope_paths"),
                "query_terms": pending["query_terms"],
                "candidates": pending["candidates"],
                "evidence_tokens": pending.get("evidence_tokens"),
                "index_paragraph_count": index.get("paragraph_count"),
                "index_built_at": index.get("built_at"),
            }
        )

    logger.info(
        "trace LLM: provider=%s model=%s scope=%s",
        llm_provider,
        model_name(llm_provider, role="trace"),
        pending.get("scope") or "(all raw/)",
    )
    result = run_skill_from_pending(pending_path, provider=llm_provider, write_output=True)
    answer = enforce_full_provenance(
        result["text"],
        index=index,
        candidates=pending.get("candidates") or [],
    )
    cleanup_pending_artifacts(pending_path)

    out: dict[str, Any] = {
        "query": pending.get("query") or query,
        "scope": pending.get("scope"),
        "scope_paths": pending.get("scope_paths") or [],
        "answer": answer,
        "provider": llm_provider,
        "model": model_name(llm_provider, role="trace"),
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
        path = save_output(
            out["query"], answer, pending["candidates"], scope=out.get("scope")
        )
        out["output_path"] = workspace_relpath(path)
        logger.info("Saved trace output to %s", path)

    n_cand = len(pending.get("candidates") or [])
    q_short = out["query"].replace("\n", " ").strip()
    if len(q_short) > 72:
        q_short = q_short[:69] + "…"
    out_rel = out.get("output_path")
    scope_bit = f" scope={out.get('scope')}" if out.get("scope") else ""
    if out_rel:
        append_log(
            "trace",
            f"created output | {q_short}{scope_bit} | candidates={n_cand} | {out_rel}",
        )
    else:
        append_log(
            "trace",
            f"ran (no-save) | {q_short}{scope_bit} | candidates={n_cand}",
        )
    return out
