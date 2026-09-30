"""Build pending JSON for trace skill (deterministic retrieval, no LLM)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from config import PENDING_DIR, TRACE_SKILL, WORKSPACE_PATH
from skill_registry import resolve_skill
from trace_index import ensure_index
from trace_retrieval import build_retrieval_pack


def _slug(query: str, max_len: int = 48) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", query).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return (safe[:max_len] or "trace").lower()


def build_user_message(pack: dict) -> str:
    terms = ", ".join(pack["query_terms"][:40])
    scope = pack.get("scope")
    scope_paths = pack.get("scope_paths") or []
    scope_lines = ""
    if scope:
        joined = ", ".join(scope_paths) if scope_paths else "(no matching paths)"
        scope_lines = (
            f"Document scope: {scope}\n"
            f"Scoped paths: {joined}\n"
            "- Answer ONLY from this scoped document/folder Evidence Pack. "
            "Do not bring in outside raw notes.\n"
        )
    return (
        f"Question: {pack['query']}\n"
        f"Language: {pack['language']}\n"
        f"{scope_lines}"
        f"Retrieval terms: {terms}\n\n"
        "Instructions:\n"
        "- Use ONLY the Evidence Pack below as factual ground truth.\n"
        "- Every factual claim needs (Source: [[path]] · #pN · Lx–Ly) plus a verbatim > quote from the pack "
        "(path is usually raw/… or upload/…).\n"
        "- In ## Provenance, paste the COMPLETE Evidence Pack paragraph text for each cited #pN "
        "(every line; no truncation).\n"
        "- When multiple paragraphs from the same note add distinct facets, cite several #pN.\n"
        "- Label inference as [AI Synthesis]. Label twitter kind as [Twitter Reference].\n"
        "- If the pack is empty or insufficient, say so — do not invent.\n\n"
        f"Evidence Pack:\n{pack['evidence_block']}\n"
    )


def build_pending(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
    scope: str | None = None,
) -> dict:
    idx = index if index is not None else ensure_index()
    pack = build_retrieval_pack(query, index=idx, provider=provider, scope=scope)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(pack["query"])
    digest = hashlib.md5(
        f"{pack['query']}|{pack.get('scope') or ''}".encode("utf-8")
    ).hexdigest()[:8]
    pending_name = f"trace-{slug}-{digest}-{stamp}.json"
    answer_name = f"trace-answer-{slug}-{digest}-{stamp}.md"

    pending = {
        "kind": "trace",
        "skill": resolve_skill("trace", str(TRACE_SKILL.relative_to(WORKSPACE_PATH))),
        "query": pack["query"],
        "scope": pack.get("scope"),
        "scope_paths": pack.get("scope_paths") or [],
        "language": pack["language"],
        "query_terms": pack["query_terms"],
        "candidates": pack["candidates"],
        "evidence_tokens": pack.get("evidence_tokens"),
        "user_message": build_user_message(pack),
        "answer_output": str((PENDING_DIR / answer_name).relative_to(WORKSPACE_PATH)),
    }
    pending["_meta"] = {
        "pending_name": pending_name,
        "pack": {k: v for k, v in pack.items() if k != "evidence_block"},
    }
    return pending


def write_pending(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
    scope: str | None = None,
) -> Path:
    pending = build_pending(query, index=index, provider=provider, scope=scope)
    name = pending.pop("_meta")["pending_name"]
    path = PENDING_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def prepare_trace(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
    scope: str | None = None,
) -> tuple[dict, Path]:
    path = write_pending(query, index=index, provider=provider, scope=scope)
    pending = json.loads(path.read_text(encoding="utf-8"))
    return pending, path
