"""Shared CLI utilities."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from build_twin_profile import build_twin_profile
from config import LOG_DIR
from log_utils import append_log
from pending_cleanup import prune_old_pending
from pipeline_progress import mark_stage_done
from refresh_index import refresh_index

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "sync_v2.log"),
            logging.StreamHandler(),
        ],
    )


def _python() -> str:
    return sys.executable


def post_ingest(summary: str = "post-ingest complete") -> None:
    scripts = Path(__file__).parent
    subprocess.run([_python(), str(scripts / "backliner.py")], check=True)
    refresh_index()
    build_twin_profile()
    append_log("ingest", summary)
    mark_stage_done("post_ingest")
    retain_days = int(os.environ.get("PENDING_RETAIN_DAYS", "7"))
    if retain_days >= 0:
        pruned = prune_old_pending(retain_days, keep_failed=True, dry_run=False)
        if pruned:
            logger.info(
                "Pruned %d stale pending file(s) older than %d days",
                len(pruned),
                retain_days,
            )
