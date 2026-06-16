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
from ingest_profiles import is_compressible, resolve_profile
from llm_provider import model_name, provider_for_role
from pipeline_progress import mark_stage_in_progress
from compress_chunking import iter_units
from posts_batch import pack_batches, posts_batch_enabled, prepare_batch_pending, split_batchable
from prepare_compress import prepare_for_unit, compression_output_path
from run_skill import run_skill_from_pending

logger = logging.getLogger(__name__)


def compress_file(rel: str, abs_path: Path, *, provider: str | None = None) -> Path | None:
    profile = resolve_profile(rel)
    if not profile or profile.get("mode") == "reference":
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
        _maybe_wiki_synth(last_out, rel, provider=provider)
        return last_out
    return None


def _maybe_wiki_synth(out: Path | None, rel: str, *, provider: str | None) -> None:
    if not out:
        return
    if os.environ.get("WIKI_SYNTH", "1").strip() in ("0", "false", "no"):
        return
    try:
        from wiki_synthesize import synthesize_compression_file

        pages = synthesize_compression_file(out, provider=provider)
        if pages:
            logger.info("Wiki-synthesize: %d page update(s) from %s", pages, rel)
    except Exception as exc:
        logger.warning("Wiki-synthesize failed for %s: %s", rel, exc)


def compress_batch(
    batch: list[tuple[str, Path, str]],
    *,
    provider: str | None = None,
) -> list[str]:
    """Compress multiple small _posts files in one LLM call."""

    pending_path = prepare_batch_pending(batch)
    result = run_skill_from_pending(
        pending_path,
        provider=provider,
        write_actions=False,
        write_output=True,
    )
    synced: list[str] = []
    for rel, abs_path, file_hash in batch:
        mark_done(rel, raw_hash=file_hash, provider=provider)
        out_rel = str(compression_output_path(rel).relative_to(WORKSPACE_PATH)).replace("\\", "/")
        out_path = WORKSPACE_PATH / out_rel
        if out_path.is_file():
            _maybe_wiki_synth(out_path, rel, provider=provider)
        synced.append(rel)
    logger.info(
        "Batch compressed %d file(s) → %s",
        len(synced),
        ", ".join(result.get("batch_paths", [])[:3]),
    )
    return synced


def _compress_targets(
    targets: list[tuple[str, Path]],
    *,
    provider: str | None = None,
) -> list[str]:
    compressed: list[str] = []
    delay = float(os.environ.get("INGEST_REQUEST_DELAY_SECONDS", "2"))

    if posts_batch_enabled():
        items = [
            (rel, abs_path, hashlib.md5(abs_path.read_bytes()).hexdigest())
            for rel, abs_path in targets
        ]
        batchable, individual = split_batchable(items)
        batches = pack_batches(batchable)
        total_steps = len(batches) + len(individual)
        step = 0
        for batch in batches:
            step += 1
            logger.info("[batch %d/%d] %d file(s)", step, total_steps, len(batch))
            try:
                compressed.extend(compress_batch(batch, provider=provider))
            except Exception as exc:
                for rel, abs_path, file_hash in batch:
                    logger.error("Batch failed for %s: %s", rel, exc)
                    mark_failed(rel, raw_hash=file_hash, error=str(exc))
            if delay > 0 and step < total_steps:
                time.sleep(delay)
        for rel, abs_path, file_hash in individual:
            step += 1
            logger.info("[%d/%d] %s", step, total_steps, rel)
            try:
                out = compress_file(rel, abs_path, provider=provider)
                if out:
                    compressed.append(rel)
            except Exception as exc:
                logger.error("Failed %s: %s", rel, exc)
                mark_failed(rel, raw_hash=file_hash, error=str(exc))
            if delay > 0 and step < total_steps:
                time.sleep(delay)
        return compressed

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


def sync_changed_files(
    *,
    provider: str | None = None,
    file_filter: str | None = None,
) -> list[str]:
    """Hash-diff sync: changed raw → compression/ (profile-routed, optional POSTS_BATCH)."""

    from orchestrator import SocraticOrchestrator
    from register_reference import register_references

    orchestrator = SocraticOrchestrator()
    changed = orchestrator.get_changed_files()
    if file_filter:
        changed = [item for item in changed if item[0] == file_filter]
    if not changed:
        logger.info("No changed raw files.")
        return []

    needs_register = any(rel.startswith("twitter/") for rel, _, _ in changed)
    to_compress: list[tuple[str, Path]] = []
    for rel, abs_path, _file_hash in changed:
        if not is_compressible(rel):
            continue
        to_compress.append((rel, abs_path))

    active = provider_for_role("sync", provider)
    logger.info(
        "Sync (changed-only): %d compressible file(s) via %s",
        len(to_compress),
        model_name(active),
    )
    compressed = _compress_targets(to_compress, provider=provider)

    for rel, _abs_path, file_hash in changed:
        if rel in compressed:
            orchestrator.cache[rel] = file_hash
    orchestrator.save_cache()

    if needs_register:
        register_references()
    return compressed


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
    targets = list_resume_targets(force=force, folder=folder)
    if limit is not None:
        targets = targets[:limit]

    logger.info("Compressing %d file(s) (%d remaining in manifest)", len(targets), len(targets))
    return _compress_targets(targets, provider=provider)
