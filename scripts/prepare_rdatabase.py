"""Build pending JSON for rdatabase skill (deterministic retrieval, no LLM)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from config import PENDING_DIR, RDATABASE_SKILL, WORKSPACE_PATH
from rdatabase_index import ensure_index
from rdatabase_retrieval import build_retrieval_pack
from skill_registry import resolve_skill


def _slug(query: str, max_len: int = 48) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", query).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return (safe[:max_len] or "rdatabase").lower()


def build_user_message(pack: dict) -> str:
    terms = ", ".join(pack["query_terms"][:40])
    return (
        f"Question: {pack['query']}\n"
        f"Language: {pack['language']}\n"
        f"Retrieval terms: {terms}\n\n"
        "Instructions:\n"
        "- Use ONLY the Evidence Pack below as factual ground truth.\n"
        "- Every factual claim needs (Source: [[raw/…]] · #pN · Lx–Ly) plus a verbatim > quote from the pack.\n"
        "- Label inference as [AI Synthesis]. Label twitter kind as [Twitter Reference].\n"
        "- If the pack is empty or insufficient, say so — do not invent.\n\n"
        f"Evidence Pack:\n{pack['evidence_block']}\n"
    )


def build_pending(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
) -> dict:
    idx = index if index is not None else ensure_index()
    pack = build_retrieval_pack(query, index=idx, provider=provider)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(query)
    digest = hashlib.md5(query.encode("utf-8")).hexdigest()[:8]
    pending_name = f"rdatabase-{slug}-{digest}-{stamp}.json"
    answer_name = f"rdatabase-answer-{slug}-{digest}-{stamp}.md"

    pending = {
        "kind": "rdatabase",
        "skill": resolve_skill("rdatabase", str(RDATABASE_SKILL.relative_to(WORKSPACE_PATH))),
        "query": query,
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
) -> Path:
    pending = build_pending(query, index=index, provider=provider)
    name = pending.pop("_meta")["pending_name"]
    path = PENDING_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def prepare_rdatabase(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
) -> tuple[dict, Path]:
    path = write_pending(query, index=index, provider=provider)
    pending = json.loads(path.read_text(encoding="utf-8"))
    return pending, path
