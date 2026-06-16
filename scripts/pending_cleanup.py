"""Pending JSON lifecycle: pair cleanup and age-based prune."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from config import PENDING_DIR, WORKSPACE_PATH, workspace_relpath

logger = logging.getLogger(__name__)


def json_actions_path(pending_path: Path) -> Path:
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    name = pending.get("actions_output")
    if name:
        path = pending_path.parent / name
    else:
        path = pending_path.with_name(
            pending_path.name.replace("ingest-", "ingest-actions-", 1)
        )
    if not path.is_absolute():
        path = WORKSPACE_PATH / path
    return path


def _should_retain_on_success() -> bool:
    return os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0").strip() == "1"


def cleanup_pending_pair(pending_path: Path) -> list[Path]:
    """Delete pending JSON and its actions sibling. Returns paths removed."""
    if _should_retain_on_success():
        return []

    pending_path = pending_path.resolve()
    removed: list[Path] = []

    try:
        actions_path = json_actions_path(pending_path)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not resolve actions for %s: %s", pending_path.name, exc)
        actions_path = None

    for path in (pending_path, actions_path):
        if path and path.exists():
            path.unlink()
            removed.append(path)
            logger.debug("Deleted %s", workspace_relpath(path))

    return removed


def _is_stale(path: Path, cutoff: datetime) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return mtime < cutoff


def prune_old_pending(
    max_age_days: int = 7,
    *,
    keep_failed: bool = True,
    dry_run: bool = True,
) -> list[Path]:
    """Remove stale pending pairs and orphan actions files."""
    if not PENDING_DIR.exists():
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    to_delete: list[Path] = []
    pending_files = sorted(PENDING_DIR.glob("ingest-*.json"))
    pending_files = [p for p in pending_files if not p.name.startswith("ingest-actions-")]

    for pending_path in pending_files:
        if max_age_days > 0 and not _is_stale(pending_path, cutoff):
            continue

        try:
            actions_path = json_actions_path(pending_path)
        except (json.JSONDecodeError, OSError):
            if keep_failed:
                continue
            actions_path = None

        if keep_failed and (actions_path is None or not actions_path.exists()):
            continue

        to_delete.append(pending_path)
        if actions_path and actions_path.exists():
            to_delete.append(actions_path)

    pending_names = {p.name for p in pending_files}
    for actions_path in PENDING_DIR.glob("ingest-actions-*.json"):
        if max_age_days > 0 and not _is_stale(actions_path, cutoff):
            continue
        stem = actions_path.name.replace("ingest-actions-", "ingest-", 1)
        if stem not in pending_names and actions_path not in to_delete:
            to_delete.append(actions_path)

    if dry_run:
        for path in to_delete:
            logger.info("[dry-run] would delete %s", workspace_relpath(path))
        return to_delete

    for path in to_delete:
        if path.exists():
            path.unlink()
            logger.info("Deleted %s", workspace_relpath(path))
    return to_delete


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pending JSON cleanup")
    parser.add_argument("--prune", action="store_true", help="Prune stale pending files by age")
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.environ.get("PENDING_RETAIN_DAYS", "7")),
        help="Delete files older than N days (0 = all eligible)",
    )
    parser.add_argument(
        "--keep-failed",
        action="store_true",
        default=True,
        help="Retain pending without actions sibling (default: true)",
    )
    parser.add_argument("--no-keep-failed", dest="keep_failed", action="store_false")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--confirm", action="store_true", help="Actually delete files")
    parser.add_argument("pending", nargs="?", help="Single pending path to delete as a pair")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.pending:
        path = Path(args.pending)
        if not path.is_absolute():
            path = WORKSPACE_PATH / path
        if args.confirm or not args.dry_run:
            removed = cleanup_pending_pair(path)
            logger.info("Removed %d file(s)", len(removed))
        else:
            try:
                actions = json_actions_path(path)
                logger.info("[dry-run] would delete %s", workspace_relpath(path))
                if actions.exists():
                    logger.info("[dry-run] would delete %s", workspace_relpath(actions))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not resolve pair: %s", exc)
        return 0

    if args.prune:
        removed = prune_old_pending(
            args.days,
            keep_failed=args.keep_failed,
            dry_run=not args.confirm,
        )
        logger.info(
            "%s %d file(s)",
            "Would delete" if not args.confirm else "Deleted",
            len(removed),
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
