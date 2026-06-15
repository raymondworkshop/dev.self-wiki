"""Batch compress raw files → compression/ via LLM skills."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import Path

from apply_compression import apply_compression_text
from compression_manifest import mark_done, mark_failed, list_resume_targets, scan_all
from config import RAW_DIR, WORKSPACE_PATH
from ingest_profiles import resolve_profile
from llm_provider import model_name, provider_for_role
from pipeline_progress import mark_stage_in_progress
from compress_chunking import iter_units
from prepare_compress import prepare_for_unit, compression_output_path
from run_skill import run_skill_from_pending

logger = logging.getLogger(__name__)


def compress_file(rel: str, abs_path: Path, *, provider: str | None = None) -> Path | None:
    profile = resolve_profile(rel)
    if not profile or profile.get("mode") == "reference":
        return None

    skill_rel = profile.get("skill")
    if not skill_rel:
        return None

    file_hash = hashlib.md5(abs_path.read_bytes()).hexdigest()
    units = iter_units(rel, abs_path)
    last_out: Path | None = None

    for chunk_rel, chunk_content in units:
        is_chunk = chunk_rel != rel
        pending_paths = prepare_for_unit(
            raw_rel=rel,
            chunk_rel=chunk_rel,
            content=chunk_content,
            file_hash=file_hash,
            is_chunk=is_chunk,
        )
        if not pending_paths:
            return None
        pending_path = pending_paths[0]
        result = run_skill_from_pending(
            pending_path,
            provider=provider,
            write_actions=False,
            write_output=True,
        )
        out_rel = result.get("output_path")
        if out_rel:
            last_out = WORKSPACE_PATH / out_rel
        elif result.get("text"):
            last_out = apply_compression_text(
                result["text"],
                rel_path=f"raw/{rel}",
                out_rel=str(compression_output_path(chunk_rel).relative_to(WORKSPACE_PATH)).replace(
                    "\\", "/"
                ),
            )

    if last_out:
        mark_done(rel, raw_hash=file_hash, provider=provider)
        return last_out
    return None


def compress_all(
    *,
    provider: str | None = None,
    limit: int | None = None,
    force: bool = False,
    folder: str | None = None,
) -> list[str]:
    active = provider_for_role("sync", provider)
    logger.info("Compress LLM: provider=%s model=%s", active, model_name(active))

    scan_all()
    mark_stage_in_progress("compression")
    compressed: list[str] = []
    targets = list_resume_targets(force=force, folder=folder)
    if limit is not None:
        targets = targets[:limit]

    logger.info("Compressing %d file(s) (%d remaining in manifest)", len(targets), len(targets))
    delay = float(os.environ.get("INGEST_REQUEST_DELAY_SECONDS", "2"))
    for i, (rel, abs_path) in enumerate(targets, 1):
        logger.info("[%d/%d] %s", i, len(targets), rel)
        file_hash = hashlib.md5(abs_path.read_bytes()).hexdigest()
        try:
            out = compress_file(rel, abs_path, provider=provider)
            if out:
                compressed.append(rel)
        except Exception as exc:
            logger.error("Failed %s: %s", rel, exc)
            mark_failed(rel, raw_hash=file_hash, error=str(exc))
        if delay > 0 and i < len(targets):
            time.sleep(delay)
    return compressed
