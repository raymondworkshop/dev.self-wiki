"""Log directory maintenance: rotation, trimming, stale artifact prune."""

from __future__ import annotations

import argparse
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from config import LOG_DIR, LOG_MD, workspace_relpath

logger = logging.getLogger(__name__)

LOG_ENTRY_RE = re.compile(r"^## \[[^\]]+\] .+$", re.MULTILINE)

# Obsolete one-shot artifacts (old launchd jobs, manual batch notes).
OBSOLETE_LOG_NAMES = frozenset(
    {
        "launchd-sync.err.log",
        "launchd-sync.out.log",
        "composer_wiki_run.log",
        "COMPOSER_WAVES.md",
    }
)

ROTATED_LOG_NAMES = frozenset(
    {
        "sync_v2.log",
        "launchd-weekly.log",
        "launchd-weekly.err.log",
    }
)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def rotate_file(
    path: Path,
    *,
    max_bytes: int | None = None,
    keep_tail_bytes: int | None = None,
) -> bool:
    """Truncate oversized log to a tail slice. Returns True if rotated."""
    if not path.is_file():
        return False

    limit = max_bytes if max_bytes is not None else _env_int("LOG_ROTATE_MAX_BYTES", 64 * 1024)
    tail = keep_tail_bytes if keep_tail_bytes is not None else _env_int("LOG_ROTATE_TAIL_BYTES", 16 * 1024)
    size = path.stat().st_size
    if size <= limit:
        return False

    data = path.read_bytes()
    slice_start = max(0, len(data) - tail)
    chunk = data[slice_start:]
    newline = chunk.find(b"\n")
    if newline >= 0:
        chunk = chunk[newline + 1 :]
    marker = b"... [truncated]\n"
    path.write_bytes(marker + chunk)
    try:
        label = workspace_relpath(path)
    except ValueError:
        label = path.name
    logger.info("Rotated %s (%d → %d bytes)", label, size, path.stat().st_size)
    return True


def trim_log_md(*, max_entries: int | None = None) -> int:
    """Keep log.md header and the most recent N ## entries."""
    if not LOG_MD.is_file():
        return 0

    max_entries = max_entries if max_entries is not None else _env_int("LOG_MD_MAX_ENTRIES", 150)
    text = LOG_MD.read_text(encoding="utf-8")
    matches = list(LOG_ENTRY_RE.finditer(text))
    if len(matches) <= max_entries:
        return 0

    first_keep = matches[-max_entries].start()
    header = text[: matches[0].start()].rstrip()
    body = text[first_keep:].lstrip("\n")
    trimmed = f"{header}\n\n{body}"
    if not trimmed.endswith("\n"):
        trimmed += "\n"
    LOG_MD.write_text(trimmed, encoding="utf-8")
    removed = len(matches) - max_entries
    logger.info("Trimmed log.md: removed %d old entries (kept %d)", removed, max_entries)
    return removed


def prune_stale_log_artifacts(
    max_age_days: int | None = None,
    *,
    dry_run: bool = False,
) -> list[Path]:
    """Remove obsolete or aged non-state files from log/."""
    max_age_days = max_age_days if max_age_days is not None else _env_int("LOG_RETAIN_DAYS", 14)
    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed: list[Path] = []

    for name in sorted(OBSOLETE_LOG_NAMES):
        path = LOG_DIR / name
        if not path.is_file():
            continue
        if name.startswith("launchd-sync.") or _is_stale(path, cutoff):
            removed.append(path)

    if dry_run:
        for path in removed:
            logger.info("[dry-run] would delete %s", workspace_relpath(path))
        return removed

    for path in removed:
        path.unlink()
        logger.info("Deleted %s", workspace_relpath(path))
    return removed


def rotate_runtime_logs() -> int:
    """Rotate known append-only runtime logs."""
    count = 0
    for name in sorted(ROTATED_LOG_NAMES):
        if rotate_file(LOG_DIR / name):
            count += 1
    return count


def _is_stale(path: Path, cutoff: datetime) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return mtime < cutoff


def maintain_logs() -> dict[str, int]:
    """Run all log maintenance steps. Called from ingest."""
    if os.environ.get("LOG_MAINTAIN", "1").strip() in {"0", "false", "no"}:
        return {}

    stats = {
        "rotated": rotate_runtime_logs(),
        "trimmed_entries": trim_log_md(),
        "pruned_artifacts": len(prune_stale_log_artifacts(dry_run=False)),
    }
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Log directory maintenance")
    parser.add_argument("--maintain", action="store_true", help="Run full maintenance")
    parser.add_argument("--rotate", action="store_true", help="Rotate oversized runtime logs")
    parser.add_argument("--trim-log-md", action="store_true", help="Trim log.md entries")
    parser.add_argument("--prune", action="store_true", help="Remove obsolete log artifacts")
    parser.add_argument("--days", type=int, default=_env_int("LOG_RETAIN_DAYS", 14))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.maintain:
        if args.dry_run:
            rotate_runtime_logs()
            trim_log_md()
            prune_stale_log_artifacts(args.days, dry_run=True)
        else:
            stats = maintain_logs()
            logger.info("Log maintenance: %s", stats)
        return 0

    if args.rotate:
        count = sum(1 for name in ROTATED_LOG_NAMES if rotate_file(LOG_DIR / name))
        logger.info("Rotated %d file(s)", count)
        return 0

    if args.trim_log_md:
        removed = trim_log_md()
        logger.info("Trimmed %d entries from log.md", removed)
        return 0

    if args.prune:
        removed = prune_stale_log_artifacts(args.days, dry_run=args.dry_run)
        logger.info("%s %d artifact(s)", "Would delete" if args.dry_run else "Deleted", len(removed))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
