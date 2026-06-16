"""Run wiki-synthesize on compression files (backfill or post-compress hook)."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from apply_ingest import apply_from_file
from ingest_profiles import resolve_profile
from llm_provider import model_name, provider_for_role
from pending_cleanup import cleanup_pending_pair, json_actions_path
from prepare_wiki_synthesize import write_pending
from run_skill import run_skill_from_pending
from wiki_synth_manifest import (
    _comp_rel,
    _file_hash,
    _raw_rel_from_compression,
    list_resume_targets,
    mark_done,
    mark_failed,
)

logger = logging.getLogger(__name__)


def synthesize_compression_file(
    comp_path: Path,
    *,
    provider: str | None = None,
) -> int:
    """Run wiki-synthesize for one compression file. Returns pages updated."""

    comp_rel = _comp_rel(comp_path)
    raw_rel = _raw_rel_from_compression(comp_rel)
    profile = resolve_profile(raw_rel)
    if not profile or not profile.get("wiki_skill") or profile.get("max_theme_updates", 0) <= 0:
        logger.info("Skip wiki-synthesize (profile): %s", comp_rel)
        mark_done(comp_rel, pages=0, content_hash=_file_hash(comp_path))
        return 0

    content_hash = _file_hash(comp_path)
    pending_path = write_pending(comp_path)
    if not pending_path:
        mark_done(comp_rel, pages=0, content_hash=content_hash)
        return 0

    try:
        run_skill_from_pending(
            pending_path,
            provider=provider,
            write_actions=True,
            write_output=False,
        )
        actions_path = json_actions_path(pending_path)
        if not actions_path.is_file():
            mark_done(comp_rel, pages=0, content_hash=content_hash)
            if os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
                cleanup_pending_pair(pending_path)
            return 0

        pages = apply_from_file(actions_path, rel_path=raw_rel)
        mark_done(comp_rel, pages=pages, content_hash=content_hash)
        if os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
            cleanup_pending_pair(pending_path)
        return pages
    except Exception as exc:
        mark_failed(comp_rel, content_hash=content_hash, error=str(exc))
        raise


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

    logger.info("Wiki-synthesizing %d compression file(s)", len(targets))
    delay = float(os.environ.get("INGEST_REQUEST_DELAY_SECONDS", "2"))
    processed: list[str] = []
    total_pages = 0

    for i, (comp_rel, abs_path) in enumerate(targets, 1):
        logger.info("[%d/%d] %s", i, len(targets), comp_rel)
        try:
            pages = synthesize_compression_file(abs_path, provider=provider)
            total_pages += pages
            processed.append(comp_rel)
        except Exception as exc:
            logger.error("Failed wiki-synthesize %s: %s", comp_rel, exc)
        if delay > 0 and i < len(targets):
            time.sleep(delay)

    logger.info("Wiki-synthesize batch: %d file(s), %d page update(s)", len(processed), total_pages)
    return processed
