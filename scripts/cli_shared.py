"""Shared CLI utilities."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from build_twin_profile import build_twin_profile
from config import LOG_DIR
from log_cleanup import maintain_logs
from log_utils import append_log
from pending_cleanup import prune_old_pending
from pipeline_progress import mark_stage_done
from refresh_index import refresh_index

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    max_bytes = int(os.environ.get("LOG_ROTATE_MAX_BYTES", str(64 * 1024)))
    backup_count = int(os.environ.get("LOG_ROTATE_BACKUP_COUNT", "1"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                LOG_DIR / "sync_v2.log",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )


def _python() -> str:
    return sys.executable


def _post_ingest_housekeeping() -> None:
    retain_days = int(os.environ.get("PENDING_RETAIN_DAYS", "7"))
    if retain_days >= 0:
        pruned = prune_old_pending(retain_days, keep_failed=True, dry_run=False)
        if pruned:
            logger.info(
                "Pruned %d stale pending file(s) older than %d days",
                len(pruned),
                retain_days,
            )

    log_stats = maintain_logs()
    if any(log_stats.values()):
        logger.info("Log maintenance: %s", log_stats)


def ingest(summary: str = "ingest complete", *, report: bool = False) -> None:
    from memex import state
    from memex.cache import write_memex_cache
    from memex.export_wiki_backlinks import export_wiki_backlinks
    from memex.fast import ingest_fast_skip, write_source_stamps
    from memex.graph import build_memex_context
    from memex.queries import find_missing_links
    from memex.search_index import write_search_index
    from memex.sources import collect_vault_pages
    from memex.write_index import write_memex_index

    if ingest_fast_skip():
        logger.info("FAST=1: vault unchanged since last ingest; skipping memex rebuild")
        refresh_index()
        build_twin_profile()
        append_log("ingest", f"{summary} (fast skip)")
        mark_stage_done("ingest")
        _post_ingest_housekeeping()
        return

    ctx = build_memex_context()
    state.set_ctx(ctx)
    write_memex_cache(ctx)
    write_search_index(ctx)
    write_memex_index(ctx)
    updated = export_wiki_backlinks(ctx)
    write_source_stamps(collect_vault_pages())
    refresh_index()
    build_twin_profile()
    append_log("ingest", summary)
    mark_stage_done("ingest")
    _post_ingest_housekeeping()

    if report or os.environ.get("REPORT", "").strip() in {"1", "true", "yes"}:
        stats = ctx.get("stats", {})
        missing = find_missing_links(ctx)
        logger.info(
            "Memex: %d pages, %d wikilinks, %d missing, %d wiki backlink files updated",
            stats.get("pages", 0),
            stats.get("wikilinks", 0),
            len(missing),
            updated,
        )
