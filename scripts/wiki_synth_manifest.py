"""Track wiki-synthesize backfill progress per compression file."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from config import COMPRESSION_DIR, LOG_DIR, WORKSPACE_PATH, workspace_relpath
from ingest_profiles import resolve_profile

MANIFEST_JSON = LOG_DIR / "wiki_synth_manifest.json"

Status = Literal["done", "pending", "no_actions", "skipped", "failed"]
STATUSES: tuple[Status, ...] = ("done", "pending", "no_actions", "skipped", "failed")

THEME_LINKS_RE = re.compile(r"^## Theme links\s*$", re.MULTILINE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _comp_rel(path: Path) -> str:
    return workspace_relpath(path)


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _compression_inner_path(comp_rel: str) -> str:
    norm = comp_rel.replace("\\", "/")
    for prefix in ("self-wiki/compression/", "compression/"):
        if norm.startswith(prefix):
            return norm[len(prefix) :]
    return norm


def compression_to_raw_rel(comp_rel: str) -> str:
    norm = comp_rel.replace("\\", "/")
    for prefix in ("self-wiki/compression/", "compression/"):
        if norm.startswith(prefix):
            norm = norm[len(prefix) :]
            break
    return f"raw/{norm}"


def _raw_rel_from_compression(comp_rel: str) -> str:
    """Return raw rel without raw/ prefix (for profile resolve)."""
    norm = compression_to_raw_rel(comp_rel)
    if norm.startswith("raw/"):
        return norm[len("raw/") :]
    return norm


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


def summarize_files(files: dict) -> dict[str, int]:
    counts = {s: 0 for s in STATUSES}
    for entry in files.values():
        status = entry.get("status", "pending")
        if status in counts:
            counts[status] += 1
    return counts


def has_theme_links(content: str) -> bool:
    return bool(THEME_LINKS_RE.search(content))


def classify_compression(path: Path, prev: dict | None = None) -> dict:
    comp_rel = _comp_rel(path)
    raw_rel = _raw_rel_from_compression(comp_rel)
    profile = resolve_profile(raw_rel)
    content_hash = _file_hash(path)

    if not profile or not profile.get("wiki_skill") or profile.get("max_theme_updates", 0) <= 0:
        return {
            "status": "skipped",
            "content_hash": content_hash,
            "updated_at": _now(),
            "note": "profile skips wiki-synthesize",
        }

    if prev and prev.get("status") in ("done", "no_actions") and prev.get("content_hash") == content_hash:
        return {**prev, "updated_at": _now()}

    if prev and prev.get("status") == "failed" and prev.get("content_hash") == content_hash:
        return {**prev, "updated_at": _now()}

    return {
        "status": "pending",
        "content_hash": content_hash,
        "raw_path": compression_to_raw_rel(comp_rel),
        "updated_at": _now(),
    }


def scan_all(*, preserve_failed: bool = True) -> dict:
    old = load_manifest()
    old_files = old.get("files", {})
    files: dict = {}

    for p in sorted(COMPRESSION_DIR.rglob("*.md", recurse_symlinks=True)):
        if not p.is_file():
            continue
        comp_rel = _comp_rel(p)
        prev = old_files.get(comp_rel, {})
        if preserve_failed and prev.get("status") == "failed":
            files[comp_rel] = {**prev, "updated_at": _now()}
            continue
        files[comp_rel] = classify_compression(p, prev)

    data = _empty_manifest()
    data["files"] = files
    if old.get("last_stop"):
        data["last_stop"] = old["last_stop"]
    save_manifest(data)
    return data


def mark_done(comp_rel: str, *, pages: int, content_hash: str) -> None:
    data = load_manifest()
    files = data.setdefault("files", {})
    status: Status = "no_actions" if pages == 0 else "done"
    files[comp_rel] = {
        "status": status,
        "content_hash": content_hash,
        "pages_updated": pages,
        "completed_at": _now(),
        "updated_at": _now(),
        "error": None,
    }
    data["last_stop"] = {"rel": comp_rel, "status": status, "at": _now(), "pages": pages}
    save_manifest(data)


def mark_failed(comp_rel: str, *, content_hash: str, error: str) -> None:
    data = load_manifest()
    files = data.setdefault("files", {})
    files[comp_rel] = {
        "status": "failed",
        "content_hash": content_hash,
        "error": str(error)[:500],
        "failed_at": _now(),
        "updated_at": _now(),
    }
    data["last_stop"] = {"rel": comp_rel, "status": "failed", "at": _now(), "error": str(error)[:200]}
    save_manifest(data)


def list_resume_targets(
    *,
    force: bool = False,
    folder: str | None = None,
    wave: str | None = None,
) -> list[tuple[str, Path]]:
    """Return (compression_rel, abs_path) for pending synthesize targets."""

    data = scan_all()
    files = data.get("files", {})
    out: list[tuple[str, Path]] = []

    for comp_rel, entry in sorted(files.items()):
        if entry.get("status") not in ("pending", "failed") and not force:
            continue
        if folder:
            prefix = folder.strip("/")
            inner = comp_rel
            for strip in ("self-wiki/compression/", "compression/"):
                if inner.startswith(strip):
                    inner = inner[len(strip) :]
                    break
            if not inner.startswith(prefix):
                continue
        abs_path = WORKSPACE_PATH / comp_rel
        if not abs_path.is_file():
            # comp_rel is logical (self-wiki/...); symlink target may differ when resolved
            resolved = abs_path.resolve()
            if resolved.is_file():
                abs_path = resolved
            else:
                continue
        if wave == "theme_links":
            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not has_theme_links(content):
                continue
        out.append((comp_rel, abs_path))

    return out


def print_status(*, folder: str | None = None) -> None:
    data = scan_all()
    summary = data.get("summary", {})
    print("Wiki-synthesize manifest:", workspace_relpath(MANIFEST_JSON))
    print(
        "  done={done}  no_actions={no_actions}  pending={pending}  "
        "skipped={skipped}  failed={failed}".format(**{k: summary.get(k, 0) for k in STATUSES})
    )
    if folder:
        prefix = folder.strip("/")
        pending = [
            r
            for r, e in data.get("files", {}).items()
            if e.get("status") == "pending"
            and _compression_inner_path(r).startswith(prefix)
        ]
        print(f"  pending under {prefix}: {len(pending)}")
