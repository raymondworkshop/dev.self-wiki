"""Pending JSON lifecycle: artifact cleanup and age-based prune."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from config import PENDING_DIR, WORKSPACE_PATH, workspace_relpath

logger = logging.getLogger(__name__)

_ACTIONS_PREFIXES = ("ingest-actions-", "wiki-synth-actions-")
_PAIR_PREFIXES = ("ingest-", "wiki-synth-")


def _resolve_artifact_path(name: str, *, base: Path | None = None) -> Path:
    path = Path(name)
    if not path.is_absolute():
        path = (base or WORKSPACE_PATH) / path
    return path


def _load_pending(pending_path: Path) -> dict | None:
    try:
        return json.loads(pending_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def pending_siblings(pending_path: Path) -> list[Path]:
    """Return artifact paths referenced by a pending JSON (actions, outputs)."""
    siblings: list[Path] = []
    pending = _load_pending(pending_path)
    if pending:
        for key in ("actions_output", "output_file", "answer_output"):
            name = pending.get(key)
            if name:
                siblings.append(_resolve_artifact_path(name, base=pending_path.parent))

    name = pending_path.name
    if name.startswith("ingest-") and not name.startswith("ingest-actions-"):
        siblings.append(
            pending_path.with_name(name.replace("ingest-", "ingest-actions-", 1))
        )
    elif name.startswith("wiki-synth-") and not name.startswith("wiki-synth-actions-"):
        slug = name.removeprefix("wiki-synth-").removesuffix(".json")
        siblings.append(pending_path.parent / f"wiki-synth-actions-{slug}.json")

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in siblings:
        resolved = path.resolve()
        if resolved == pending_path.resolve() or resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def json_actions_path(pending_path: Path) -> Path:
    pending = _load_pending(pending_path)
    if not pending:
        raise ValueError(f"Invalid pending JSON: {pending_path.name}")

    name = pending.get("actions_output")
    if name:
        return _resolve_artifact_path(name, base=pending_path.parent)

    stem = pending_path.name
    if stem.startswith("ingest-") and not stem.startswith("ingest-actions-"):
        return pending_path.with_name(stem.replace("ingest-", "ingest-actions-", 1))
    if stem.startswith("wiki-synth-") and not stem.startswith("wiki-synth-actions-"):
        slug = stem.removeprefix("wiki-synth-").removesuffix(".json")
        return pending_path.parent / f"wiki-synth-actions-{slug}.json"
    raise ValueError(f"No actions_output in pending: {pending_path.name}")


def _should_retain_on_success() -> bool:
    return os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0").strip() == "1"


def _is_action_pair_pending(pending_path: Path) -> bool:
    if pending_path.name.startswith(_ACTIONS_PREFIXES):
        return False
    if pending_path.name.startswith(_PAIR_PREFIXES):
        return True
    pending = _load_pending(pending_path)
    return bool(pending and (pending.get("kind") == "ingest" or pending.get("actions_output")))


def _pending_json_files() -> list[Path]:
    if not PENDING_DIR.exists():
        return []
    return sorted(
        path
        for path in PENDING_DIR.glob("*.json")
        if not path.name.startswith(_ACTIONS_PREFIXES)
        and not path.name.endswith(".applied.json")
    )


def cleanup_pending_pair(pending_path: Path) -> list[Path]:
    """Delete pending JSON and related artifacts. Returns paths removed."""
    return cleanup_pending_artifacts(pending_path)


def cleanup_pending_artifacts(pending_path: Path) -> list[Path]:
    """Delete pending JSON and related artifacts. Returns paths removed."""
    if _should_retain_on_success():
        return []

    pending_path = pending_path.resolve()
    targets = [pending_path, *pending_siblings(pending_path)]
    removed: list[Path] = []
    for path in targets:
        if path.exists():
            path.unlink()
            removed.append(path)
            logger.debug("Deleted %s", workspace_relpath(path))
    return removed


def _is_stale(path: Path, cutoff: datetime) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return mtime < cutoff


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def prune_old_pending(
    max_age_days: int = 7,
    *,
    keep_failed: bool = True,
    dry_run: bool = True,
) -> list[Path]:
    """Remove stale pending artifacts across all pipeline kinds."""
    if not PENDING_DIR.exists():
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    to_delete: list[Path] = []
    pending_files = _pending_json_files()
    pending_names = {path.name for path in pending_files}

    for pending_path in pending_files:
        if max_age_days > 0 and not _is_stale(pending_path, cutoff):
            continue

        if _is_action_pair_pending(pending_path):
            try:
                actions_path = json_actions_path(pending_path)
            except (ValueError, json.JSONDecodeError, OSError):
                if keep_failed:
                    continue
                actions_path = None

            if keep_failed and (actions_path is None or not actions_path.exists()):
                continue

            to_delete.append(pending_path)
            if actions_path and actions_path.exists():
                to_delete.append(actions_path)
            continue

        to_delete.append(pending_path)
        for sibling in pending_siblings(pending_path):
            if sibling.exists():
                to_delete.append(sibling)

    for actions_path in PENDING_DIR.glob("ingest-actions-*.json"):
        if max_age_days > 0 and not _is_stale(actions_path, cutoff):
            continue
        stem = actions_path.name.replace("ingest-actions-", "ingest-", 1)
        if stem not in pending_names:
            to_delete.append(actions_path)

    for actions_path in PENDING_DIR.glob("wiki-synth-actions-*.json"):
        if max_age_days > 0 and not _is_stale(actions_path, cutoff):
            continue
        slug = actions_path.name.removeprefix("wiki-synth-actions-").removesuffix(".json")
        stem = f"wiki-synth-{slug}.json"
        if stem not in pending_names:
            to_delete.append(actions_path)

    for output_path in PENDING_DIR.glob("lint-output-*.md"):
        if max_age_days > 0 and not _is_stale(output_path, cutoff):
            continue
        stamp = output_path.name.removeprefix("lint-output-").removesuffix(".md")
        if f"lint-{stamp}.json" not in pending_names and output_path not in to_delete:
            to_delete.append(output_path)

    for applied_path in PENDING_DIR.glob("*.applied.json"):
        if max_age_days > 0 and not _is_stale(applied_path, cutoff):
            continue
        to_delete.append(applied_path)

    to_delete = _dedupe_paths(to_delete)

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
