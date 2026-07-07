"""Basic CLI command handlers."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from apply_ingest import apply_from_file
from config import WORKSPACE_PATH
from pending_cleanup import cleanup_pending_pair, json_actions_path
from run_skill import run_skill_from_pending
from cli_shared import ingest

logger = logging.getLogger(__name__)


def cmd_run_skill(args: argparse.Namespace) -> int:
    pending = Path(args.pending)
    if not pending.is_absolute():
        pending = WORKSPACE_PATH / pending
    run_skill_from_pending(pending, provider=args.provider)
    if args.apply:
        actions_path = json_actions_path(pending)
        count = apply_from_file(actions_path, rel_path=args.raw)
        logger.info("Applied %d page update(s)", count)
        if count >= 0 and os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
            cleanup_pending_pair(pending)
    return 0


def cmd_apply_ingest(args: argparse.Namespace) -> int:
    actions = Path(args.file)
    if not actions.is_absolute():
        actions = WORKSPACE_PATH / actions
    count = apply_from_file(actions, rel_path=args.raw)
    logger.info("Applied %d page update(s)", count)
    if count >= 0 and args.pending:
        pending = Path(args.pending)
        if not pending.is_absolute():
            pending = WORKSPACE_PATH / pending
        if os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
            cleanup_pending_pair(pending)
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    ingest(args.summary, report=getattr(args, "report", False))
    return 0
