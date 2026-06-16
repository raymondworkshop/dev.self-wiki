"""Pack small changed _posts files into token-budgeted batch ingest units."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from ingest_profiles import resolve_profile
from lang_utils import detect_language, epistemic_label_instruction, language_output_instruction
from query_retrieval import estimate_tokens
from skill_registry import resolve_skill
from config import PENDING_DIR, WORKSPACE_PATH
from prepare_compress import compression_output_path


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in ("1", "true", "yes")


def posts_batch_enabled() -> bool:
    return _env_flag("POSTS_BATCH")


def batch_limits() -> dict[str, int]:
    return {
        "max_tokens": int(os.environ.get("MAX_INGEST_BATCH_TOKENS", "150000")),
        "max_files": int(os.environ.get("MAX_INGEST_BATCH_FILES", "8")),
        "max_lines": int(os.environ.get("POSTS_BATCH_MAX_LINES", "400")),
    }


def file_line_count(abs_path: Path) -> int:
    try:
        return len(abs_path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def is_batch_eligible(rel: str, abs_path: Path) -> bool:
    profile = resolve_profile(rel)
    if not profile or not profile.get("batch_eligible"):
        return False
    return file_line_count(abs_path) <= batch_limits()["max_lines"]


def split_batchable(
    items: list[tuple[str, Path, str]],
) -> tuple[list[tuple[str, Path, str]], list[tuple[str, Path, str]]]:
    batchable: list[tuple[str, Path, str]] = []
    individual: list[tuple[str, Path, str]] = []
    for rel, abs_path, file_hash in items:
        if is_batch_eligible(rel, abs_path):
            batchable.append((rel, abs_path, file_hash))
        else:
            individual.append((rel, abs_path, file_hash))
    return batchable, individual


def pack_batches(
    items: list[tuple[str, Path, str]],
) -> list[list[tuple[str, Path, str]]]:
    """Greedy pack by estimated raw token budget and file cap."""

    limits = batch_limits()
    batches: list[list[tuple[str, Path, str]]] = []
    current: list[tuple[str, Path, str]] = []
    token_sum = 0

    for rel, abs_path, file_hash in items:
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tokens = estimate_tokens(content)
        would_exceed_tokens = token_sum + tokens > limits["max_tokens"]
        would_exceed_files = len(current) >= limits["max_files"]
        if current and (would_exceed_tokens or would_exceed_files):
            batches.append(current)
            current = []
            token_sum = 0
        current.append((rel, abs_path, file_hash))
        token_sum += tokens

    if current:
        batches.append(current)
    return batches


def _sanitize_slug(rel_path: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", rel_path).strip("-")
    return slug[:60] or "batch"


def _batch_json_instruction(count: int) -> str:
    return f"""
BATCH MODE ({count} sources): Reply with ONE JSON object only (no markdown fences):
{{"digests": [{{"raw_path": "raw/_posts/example.md", "body": "<complete compression markdown per ingest-summary>"}}, ...]}}
- One digest per source below; each body is a full compression file (YAML + body, ≤80 lines prose).
- raw_path must match the source path exactly.
- Match each source's language; do not translate.
"""


def build_batch_user_message(sources: list[dict], *, skill_rel: str) -> str:
    parts = [
        f"Skill: {skill_rel}",
        _batch_json_instruction(len(sources)),
        epistemic_label_instruction(),
        "",
    ]
    for src in sources:
        parts.extend(
            [
                f"### Source: raw/{src['rel'].lstrip('raw/')}",
                language_output_instruction(src["language"]),
                "---",
                src["content"],
                "---",
                "",
            ]
        )
    return "\n".join(parts)


def prepare_batch_pending(batch: list[tuple[str, Path, str]]) -> Path:
    profile = resolve_profile(batch[0][0])
    profile_skill = (profile or {}).get("skill") or "skills/ingest-summary.md"
    skill_rel = resolve_skill(
        "compression",
        profile_skill,
        raw_rel=batch[0][0],
        current_skill=(profile or {}).get("skill"),
    )
    sources: list[dict] = []
    output_files: list[str] = []
    for rel, abs_path, file_hash in batch:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        sources.append(
            {
                "rel": rel,
                "hash": file_hash,
                "language": detect_language(content),
                "content": content,
            }
        )
        out_rel = str(compression_output_path(rel).relative_to(WORKSPACE_PATH)).replace(
            "\\", "/"
        )
        output_files.append(out_rel)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _sanitize_slug(",".join(s["rel"] for s in sources[:2]))
    pending_path = PENDING_DIR / f"compress-batch-{slug}-{ts}.json"
    payload = {
        "kind": "compression",
        "batch": True,
        "skill": skill_rel,
        "sources": sources,
        "output_files": output_files,
        "user_message": build_batch_user_message(sources, skill_rel=skill_rel),
        "created_at": datetime.now().isoformat(),
    }
    pending_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return pending_path
