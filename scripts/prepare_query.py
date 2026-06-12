"""Build pending JSON for query skill (deterministic retrieval, no LLM)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from config import PENDING_DIR, QUERY_SKILL, WORKSPACE_PATH
from query_retrieval import build_retrieval_pack, load_index
from build_twin_profile import profile_excerpt_for_query


def _slug(query: str, max_len: int = 48) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", query).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return (safe[:max_len] or "query").lower()


def build_user_message(pack: dict) -> str:
    strong_label = "true" if pack["strong_profile"] else "false"
    terms = ", ".join(pack["query_terms"][:40])
    return (
        f"Question: {pack['query']}\n"
        f"Detected profile: {pack['profile']} (strong: {strong_label})\n"
        f"Language: {pack['language']}\n"
        f"Retrieval terms: {terms}\n\n"
        "Digital Twin Profile (deterministic snapshot):\n"
        f"{profile_excerpt_for_query(pack['query'], pack['query_terms'])}\n\n"
        f"Profile instruction:\n{pack['profile_instruction']}\n\n"
        f"Evidence Pack:\n{pack['evidence_block']}\n"
    )


def build_pending(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
) -> dict:
    pack = build_retrieval_pack(query, index=index, provider=provider)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(query)
    digest = hashlib.md5(query.encode("utf-8")).hexdigest()[:8]
    pending_name = f"query-{slug}-{digest}-{stamp}.json"
    answer_name = f"query-answer-{slug}-{digest}-{stamp}.md"

    pending = {
        "kind": "query",
        "skill": str(QUERY_SKILL.relative_to(WORKSPACE_PATH)),
        "query": query,
        "profile": pack["profile"],
        "strong_profile": pack["strong_profile"],
        "profile_scores": pack["profile_scores"],
        "language": pack["language"],
        "query_terms": pack["query_terms"],
        "candidates": pack["candidates"],
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
    path.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def prepare_query(
    query: str,
    *,
    index: dict | None = None,
    provider: str | None = None,
) -> tuple[dict, Path]:
    """Return (pending dict, path) for CLI / interactive flows."""
    if index is None:
        index = load_index(required=False)
    pending = build_pending(query, index=index, provider=provider)
    name = pending.pop("_meta")["pending_name"]
    path = PENDING_DIR / name
    path.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    pending["_pending_path"] = str(path.relative_to(WORKSPACE_PATH))
    return pending, path
