"""Run wiki-synthesize on raw files."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from apply_ingest import apply_from_file
from ingest_profiles import resolve_profile
from llm_provider import model_name, provider_for_role
from pending_cleanup import cleanup_pending_pair, json_actions_path
from prepare_wiki_synthesize import write_pending_units
from run_skill import run_skill_from_pending
from wiki_synth_manifest import (
    _file_hash,
    _raw_rel,
    canonical_raw_rel,
    list_resume_targets,
    lookup_file_entry,
    mark_done,
    mark_failed,
    raw_rel_inner,
)

logger = logging.getLogger(__name__)


def synthesize_raw_file(
    raw_path: Path,
    *,
    provider: str | None = None,
) -> int:
    """Run wiki-synthesize for one raw file (chunked if needed). Returns pages updated."""

    raw_rel = _raw_rel(raw_path)
    inner = raw_rel_inner(raw_rel)
    profile = resolve_profile(inner)
    if not profile or not profile.get("wiki_skill") or profile.get("max_theme_updates", 0) <= 0:
        logger.info("Skip wiki-synthesize (profile): %s", raw_rel)
        mark_done(raw_rel, pages=0, content_hash=_file_hash(raw_path))
        return 0

    content_hash = _file_hash(raw_path)
    pending_paths = write_pending_units(raw_path)
    if not pending_paths:
        mark_done(raw_rel, pages=0, content_hash=content_hash)
        return 0

    total_pages = 0
    try:
        for pending_path in pending_paths:
            run_skill_from_pending(
                pending_path,
                provider=provider,
                write_actions=True,
                write_output=False,
            )
            actions_path = json_actions_path(pending_path)
            if not actions_path.is_file():
                if os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
                    cleanup_pending_pair(pending_path)
                continue
            pages = apply_from_file(actions_path, rel_path=inner)
            total_pages += pages
            if os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
                cleanup_pending_pair(pending_path)

        mark_done(raw_rel, pages=total_pages, content_hash=content_hash)
        return total_pages
    except Exception as exc:
        mark_failed(raw_rel, content_hash=content_hash, error=str(exc))
        raise


def sync_changed_raw_files(
    *,
    provider: str | None = None,
    file_filter: str | None = None,
) -> list[str]:
    """Hash-diff sync: only wiki-synthesize changed raw files not already up to date."""

    from orchestrator import SocraticOrchestrator
    from wiki_synth_manifest import load_manifest, lookup_file_entry, seed_manifest_from_wiki_provenance

    orchestrator = SocraticOrchestrator()
    changed = orchestrator.get_changed_files()
    if file_filter:
        rel_filter = file_filter.removeprefix("raw/").removeprefix("self-wiki/raw/")
        changed = [item for item in changed if item[0] == rel_filter]
    if not changed:
        logger.info("No changed raw files.")
        return []

    manifest = load_manifest()
    seed_manifest_from_wiki_provenance(manifest)
    manifest = load_manifest()
    files = manifest.get("files", {})
    to_process: list[tuple[str, Path, str, str]] = []
    skipped_manifest = 0
    skipped_profile = 0

    for rel, abs_path, file_hash in changed:
        raw_rel = canonical_raw_rel(f"raw/{rel}")
        profile = resolve_profile(rel)
        if not profile or not profile.get("wiki_skill") or profile.get("max_theme_updates", 0) <= 0:
            orchestrator.cache[rel] = file_hash
            skipped_profile += 1
            continue
        entry = lookup_file_entry(files, raw_rel)
        if entry.get("status") in ("done", "no_actions") and entry.get("content_hash") == file_hash:
            orchestrator.cache[rel] = file_hash
            skipped_manifest += 1
            continue
        to_process.append((raw_rel, abs_path, rel, file_hash))

    if skipped_manifest:
        logger.info(
            "Skipping %d unchanged file(s) already wiki-synthesized (manifest)",
            skipped_manifest,
        )
    if not to_process:
        orchestrator.save_cache()
        logger.info("Nothing to sync.")
        return []

    active = provider_for_role("wiki_synthesize", provider)
    logger.info(
        "Sync (changed-only): %d raw file(s) via %s",
        len(to_process),
        model_name(active),
    )
    delay = float(os.environ.get("INGEST_REQUEST_DELAY_SECONDS", "2"))
    processed: list[str] = []
    for i, (raw_rel, abs_path, rel, file_hash) in enumerate(to_process, 1):
        logger.info("[%d/%d] %s", i, len(to_process), raw_rel)
        try:
            synthesize_raw_file(abs_path, provider=provider)
            processed.append(raw_rel)
        except Exception as exc:
            logger.error("Failed wiki-synthesize %s: %s", raw_rel, exc)
        orchestrator.cache[rel] = file_hash
        if delay > 0 and i < len(to_process):
            time.sleep(delay)

    orchestrator.save_cache()
    return processed


def synthesize_all(
    *,
    provider: str | None = None,
    limit: int | None = None,
    force: bool = False,
    folder: str | None = None,
    wave: str | None = None,
) -> list[str]:
    active = provider_for_role("sync", provider)
    logger.info("Wiki-synthesize LLM: provider=%s model=%s", active, model_name(active))

    targets = list_resume_targets(force=force, folder=folder, wave=wave)
    if limit is not None:
        targets = targets[:limit]

    logger.info("Wiki-synthesizing %d raw file(s)", len(targets))
    delay = float(os.environ.get("INGEST_REQUEST_DELAY_SECONDS", "2"))
    processed: list[str] = []
    total_pages = 0

    for i, (raw_rel, abs_path) in enumerate(targets, 1):
        logger.info("[%d/%d] %s", i, len(targets), raw_rel)
        try:
            pages = synthesize_raw_file(abs_path, provider=provider)
            total_pages += pages
            processed.append(raw_rel)
        except Exception as exc:
            logger.error("Failed wiki-synthesize %s: %s", raw_rel, exc)
        if delay > 0 and i < len(targets):
            time.sleep(delay)

    logger.info("Wiki-synthesize batch: %d file(s), %d page update(s)", len(processed), total_pages)
    return processed
