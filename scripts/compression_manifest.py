"""Track compression progress per raw file for resume/stop points."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from config import LOG_DIR, RAW_DIR, WORKSPACE_PATH
from ingest_profiles import is_compressible
from prepare_compress import compression_output_path

MANIFEST_JSON = LOG_DIR / "compression_manifest.json"
PROGRESS_MD = LOG_DIR / "compression_progress.md"

Status = Literal["done", "pending", "stale", "failed", "skipped"]

STATUSES: tuple[Status, ...] = ("done", "pending", "stale", "failed", "skipped")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _raw_rel(abs_path: Path) -> str:
    return str(abs_path.relative_to(RAW_DIR)).replace("\\", "/")


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _compression_rel(rel: str) -> str:
    out = compression_output_path(f"raw/{rel}")
    return str(out.relative_to(WORKSPACE_PATH)).replace("\\", "/")


def _empty_manifest() -> dict:
    return {
        "version": 1,
        "updated_at": _now(),
        "summary": {s: 0 for s in STATUSES},
        "last_stop": None,
        "files": {},
    }


def load_manifest() -> dict:
    if not MANIFEST_JSON.exists():
        return _empty_manifest()
    try:
        data = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_manifest()
    data.setdefault("files", {})
    data.setdefault("summary", {s: 0 for s in STATUSES})
    return data


def save_manifest(data: dict) -> None:
    data["updated_at"] = _now()
    data["summary"] = summarize_files(data.get("files", {}))
    MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    write_progress_md(data)
    _refresh_pipeline()


def _refresh_pipeline() -> None:
    try:
        from pipeline_progress import refresh_all

        refresh_all(rescan_compression=False)
    except Exception:
        pass


def summarize_files(files: dict) -> dict[str, int]:
    counts = {s: 0 for s in STATUSES}
    for entry in files.values():
        status = entry.get("status", "pending")
        if status in counts:
            counts[status] += 1
    return counts


def classify_file(rel: str, abs_path: Path, prev: dict | None = None) -> dict:
    """Return manifest entry for one raw file."""

    if not is_compressible(rel):
        return {"status": "skipped", "raw_hash": None, "updated_at": _now()}

    raw_hash = _file_hash(abs_path)
    out = compression_output_path(f"raw/{rel}")

    if prev and prev.get("status") == "failed" and prev.get("raw_hash") == raw_hash:
        return {**prev, "updated_at": _now()}

    if not out.exists():
        return {
            "status": "pending",
            "raw_hash": raw_hash,
            "compression_path": None,
            "updated_at": _now(),
        }

    if prev and prev.get("status") == "done" and prev.get("raw_hash") == raw_hash:
        return {
            **prev,
            "status": "done",
            "compression_path": _compression_rel(rel),
            "updated_at": _now(),
        }

    if prev and prev.get("raw_hash") and prev.get("raw_hash") != raw_hash:
        return {
            "status": "stale",
            "raw_hash": raw_hash,
            "compression_path": _compression_rel(rel),
            "updated_at": _now(),
            "note": "raw changed since last digest",
        }

    return {
        "status": "done",
        "raw_hash": raw_hash,
        "compression_path": _compression_rel(rel),
        "completed_at": (prev or {}).get("completed_at") or _now(),
        "provider": (prev or {}).get("provider"),
        "updated_at": _now(),
    }


def scan_all(*, preserve_failed: bool = True) -> dict:
    """Rebuild manifest from raw/ + compression/ on disk."""

    old = load_manifest()
    old_files = old.get("files", {})
    files: dict = {}

    for p in sorted(RAW_DIR.rglob("*.md", recurse_symlinks=True)):
        if not p.is_file():
            continue
        rel = _raw_rel(p)
        prev = old_files.get(rel, {})
        if preserve_failed and prev.get("status") == "failed":
            files[rel] = {**prev, "updated_at": _now()}
            continue
        files[rel] = classify_file(rel, p, prev)

    data = _empty_manifest()
    data["files"] = files
    if old.get("last_stop"):
        data["last_stop"] = old["last_stop"]
    save_manifest(data)
    return data


def mark_done(
    rel: str,
    *,
    raw_hash: str,
    provider: str | None = None,
    compression_path: str | None = None,
) -> None:
    data = load_manifest()
    files = data.setdefault("files", {})
    files[rel] = {
        "status": "done",
        "raw_hash": raw_hash,
        "compression_path": compression_path or _compression_rel(rel),
        "completed_at": _now(),
        "provider": provider,
        "updated_at": _now(),
        "error": None,
    }
    data["last_stop"] = {"rel": rel, "status": "done", "at": _now()}
    save_manifest(data)


def mark_failed(rel: str, *, raw_hash: str, error: str) -> None:
    data = load_manifest()
    files = data.setdefault("files", {})
    files[rel] = {
        "status": "failed",
        "raw_hash": raw_hash,
        "error": str(error)[:500],
        "failed_at": _now(),
        "updated_at": _now(),
    }
    data["last_stop"] = {
        "rel": rel,
        "status": "failed",
        "at": _now(),
        "error": str(error)[:200],
    }
    save_manifest(data)


def list_resume_targets(
    *,
    force: bool = False,
    include_failed: bool = True,
    folder: str | None = None,
) -> list[tuple[str, Path]]:
    data = load_manifest()
    files = data.get("files", {})

    targets: list[tuple[str, Path]] = []
    for p in sorted(RAW_DIR.rglob("*.md", recurse_symlinks=True)):
        if not p.is_file():
            continue
        rel = _raw_rel(p)
        if folder:
            prefix = folder.rstrip("/") + "/"
            if not rel.startswith(prefix) and rel != folder.rstrip("/"):
                continue
        if not is_compressible(rel):
            continue

        entry = files.get(rel)
        if not entry:
            entry = classify_file(rel, p)
            files[rel] = entry

        status = entry.get("status")
        if force:
            targets.append((rel, p))
            continue
        if status in ("pending", "stale"):
            targets.append((rel, p))
        elif status == "failed" and include_failed:
            targets.append((rel, p))

    return targets


def write_progress_md(data: dict | None = None) -> Path:
    if data is None:
        data = load_manifest()
    files: dict = data.get("files", {})
    summary = data.get("summary") or summarize_files(files)
    last_stop = data.get("last_stop")

    by_status: dict[str, list[str]] = {s: [] for s in STATUSES}
    for rel, entry in sorted(files.items()):
        st = entry.get("status", "pending")
        if st in by_status:
            by_status[st].append(rel)

    lines = [
        "# Compression progress",
        "",
        f"Updated: {data.get('updated_at', _now())}",
        "",
        "Machine index: `log/compression_manifest.json`",
        "",
        "## Summary",
        "",
        "| Status | Meaning | Count |",
        "|--------|---------|------:|",
        "| done | digest exists, raw unchanged | "
        f"{summary.get('done', 0)} |",
        "| pending | not yet digested | "
        f"{summary.get('pending', 0)} |",
        "| stale | raw changed since last digest | "
        f"{summary.get('stale', 0)} |",
        "| failed | last run errored — will retry | "
        f"{summary.get('failed', 0)} |",
        "| skipped | twitter / memex / non-compressible | "
        f"{summary.get('skipped', 0)} |",
        "",
    ]

    if last_stop:
        lines.extend(
            [
                "## Last stop",
                "",
                f"- **File:** `{last_stop.get('rel')}`",
                f"- **Status:** {last_stop.get('status')}",
                f"- **At:** {last_stop.get('at')}",
            ]
        )
        if last_stop.get("error"):
            lines.append(f"- **Error:** {last_stop.get('error')}")
        lines.append("")

    lines.extend(
        [
            "## Resume",
            "",
            "```bash",
            "make compress-status          # refresh + show counts",
            "make compress LIMIT=50        # next batch (skips done)",
            "make compress FOLDER=origin-apple-notes LIMIT=30",
            "make build                    # full cloud backfill",
            "```",
            "",
        ]
    )

    def _section(title: str, status: Status, limit: int = 80) -> None:
        items = by_status.get(status, [])
        if not items:
            return
        lines.extend([f"## {title} ({len(items)})", ""])
        for rel in items[:limit]:
            lines.append(f"- [ ] `{rel}`" if status != "done" else f"- [x] `{rel}`")
        if len(items) > limit:
            lines.append(f"- … and {len(items) - limit} more (see manifest JSON)")
        lines.append("")

    _section("Pending", "pending")
    _section("Stale (re-compress)", "stale")
    _section("Failed", "failed")
    _section("Done (recent sample)", "done", limit=30)

    PROGRESS_MD.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_MD.write_text("\n".join(lines), encoding="utf-8")
    return PROGRESS_MD


def print_status(*, folder: str | None = None) -> dict:
    data = scan_all()
    summary = data["summary"]
    total = sum(summary.values())
    compressible = summary.get("done", 0) + summary.get("pending", 0) + summary.get("stale", 0) + summary.get("failed", 0)
    remaining = summary.get("pending", 0) + summary.get("stale", 0) + summary.get("failed", 0)

    print(f"Compression progress ({total} raw .md files scanned)")
    print(f"  done:    {summary.get('done', 0):4d}")
    print(f"  pending: {summary.get('pending', 0):4d}")
    print(f"  stale:   {summary.get('stale', 0):4d}")
    print(f"  failed:  {summary.get('failed', 0):4d}")
    print(f"  skipped: {summary.get('skipped', 0):4d}")
    if compressible:
        pct = 100 * summary.get("done", 0) / compressible
        print(f"  progress: {summary.get('done', 0)}/{compressible} ({pct:.1f}%) — {remaining} remaining")
    if data.get("last_stop"):
        ls = data["last_stop"]
        print(f"  last stop: [{ls.get('status')}] {ls.get('rel')}")
    print(f"\nHuman report: {PROGRESS_MD.relative_to(WORKSPACE_PATH)}")
    print(f"Machine index: {MANIFEST_JSON.relative_to(WORKSPACE_PATH)}")

    if folder:
        targets = list_resume_targets(folder=folder)
        print(f"\nNext in {folder}: {len(targets)} file(s)")
        for rel, _ in targets[:10]:
            print(f"  - {rel}")

    return data
