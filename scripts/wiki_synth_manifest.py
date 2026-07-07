"""Track wiki-synthesize backfill progress per raw file."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from config import LOG_DIR, RAW_DIR, WORKSPACE_PATH, workspace_relpath
from ingest_profiles import resolve_profile

MANIFEST_JSON = LOG_DIR / "wiki_synth_manifest.json"

Status = Literal["done", "pending", "no_actions", "skipped", "failed"]
STATUSES: tuple[Status, ...] = ("done", "pending", "no_actions", "skipped", "failed")

THEME_LINKS_RE = re.compile(r"^## Theme links\s*$", re.MULTILINE)
PROVENANCE_RAW_RE = re.compile(
    r"\(Source:\s*\[\[(?:raw/|self-wiki/raw/)([^\]]+)\]\]\)", re.IGNORECASE
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_raw_rel(raw_rel: str) -> str:
    """Canonical manifest key (self-wiki/raw/...)."""
    norm = raw_rel.replace("\\", "/")
    if norm.startswith("self-wiki/raw/"):
        return norm
    if norm.startswith("raw/"):
        return f"self-wiki/{norm}"
    return f"self-wiki/raw/{norm.lstrip('/')}"


def _raw_rel(path: Path) -> str:
    return canonical_raw_rel(workspace_relpath(path))


def _raw_inner_path(raw_rel: str) -> str:
    norm = raw_rel.replace("\\", "/")
    for prefix in ("self-wiki/raw/", "raw/"):
        if norm.startswith(prefix):
            return norm[len(prefix) :]
    return norm


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def compression_to_raw_rel(comp_rel: str) -> str:
    """Legacy: map compression path to canonical raw path."""
    norm = comp_rel.replace("\\", "/")
    for prefix in ("self-wiki/compression/", "compression/"):
        if norm.startswith(prefix):
            norm = norm[len(prefix) :]
            break
    return canonical_raw_rel(f"raw/{norm}")


def raw_rel_inner(raw_rel: str) -> str:
    norm = raw_rel.replace("\\", "/")
    if norm.startswith("raw/"):
        return norm[len("raw/") :]
    if norm.startswith("self-wiki/raw/"):
        return norm[len("self-wiki/raw/") :]
    return norm


def _empty_manifest() -> dict:
    return {
        "version": 2,
        "updated_at": _now(),
        "summary": {s: 0 for s in STATUSES},
        "last_stop": None,
        "files": {},
    }


_STATUS_RANK = {"done": 5, "no_actions": 4, "failed": 3, "pending": 2, "skipped": 1}


def _key_variants(raw_rel: str) -> list[str]:
    canon = canonical_raw_rel(raw_rel)
    inner = _raw_inner_path(canon)
    return list(dict.fromkeys([canon, f"raw/{inner}", inner]))


def lookup_file_entry(files: dict, raw_rel: str) -> dict:
    for key in _key_variants(raw_rel):
        if key in files:
            return files[key]
    return {}


def normalize_manifest_files(files: dict) -> dict:
    """Merge legacy compression/raw key variants into canonical self-wiki/raw/... keys."""
    merged: dict[str, dict] = {}
    for key, entry in files.items():
        if "/compression/" in key.replace("\\", "/") or key.startswith("compression/"):
            canon_key = compression_to_raw_rel(key)
        else:
            canon_key = canonical_raw_rel(key)
        entry = {**entry, "raw_path": canon_key}
        cur = merged.get(canon_key)
        if cur is None:
            merged[canon_key] = entry
            continue
        cur_rank = _STATUS_RANK.get(cur.get("status"), 0)
        new_rank = _STATUS_RANK.get(entry.get("status"), 0)
        if new_rank > cur_rank:
            merged[canon_key] = entry
        elif new_rank == cur_rank and entry.get("content_hash") == cur.get("content_hash"):
            merged[canon_key] = entry
    return merged


def load_manifest() -> dict:
    if not MANIFEST_JSON.exists():
        return _empty_manifest()
    try:
        data = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_manifest()
    data.setdefault("files", {})
    data.setdefault("summary", {s: 0 for s in STATUSES})
    normalized = normalize_manifest_files(data["files"])
    if normalized != data["files"]:
        data["files"] = normalized
        data["summary"] = summarize_files(normalized)
        save_manifest(data)
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


def classify_raw(path: Path, prev: dict | None = None) -> dict:
    raw_rel = _raw_rel(path)
    inner = raw_rel_inner(raw_rel)
    profile = resolve_profile(inner)
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
        "raw_path": raw_rel,
        "updated_at": _now(),
    }


def _migrate_legacy_keys(files: dict) -> dict:
    return normalize_manifest_files(files)


def seed_manifest_from_wiki_provenance(data: dict | None = None) -> int:
    """Mark raw files as no_actions when wiki already cites them as sources."""
    from config import WIKI_DIR

    data = data or load_manifest()
    files = data.setdefault("files", {})
    cited_raw: set[str] = set()
    for path in WIKI_DIR.rglob("*.md", recurse_symlinks=True):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in PROVENANCE_RAW_RE.finditer(text):
            cited_raw.add(canonical_raw_rel(f"raw/{match.group(1).strip()}"))

    updated = 0
    for raw_rel in cited_raw:
        abs_path = WORKSPACE_PATH / raw_rel
        if not abs_path.is_file():
            resolved = abs_path.resolve()
            if resolved.is_file():
                abs_path = resolved
            else:
                continue
        content_hash = _file_hash(abs_path)
        entry = lookup_file_entry(files, raw_rel)
        if entry.get("status") in ("done", "no_actions") and entry.get("content_hash") == content_hash:
            continue
        canon = canonical_raw_rel(raw_rel)
        files[canon] = {
            "status": "no_actions",
            "content_hash": content_hash,
            "raw_path": canon,
            "note": "seeded from wiki provenance",
            "updated_at": _now(),
        }
        updated += 1
    if updated:
        save_manifest(data)
    return updated


def scan_all(*, preserve_failed: bool = True) -> dict:
    old = load_manifest()
    seeded = seed_manifest_from_wiki_provenance(old)
    if seeded:
        old = load_manifest()
    old_files = old.get("files", {})
    files: dict = {}

    for p in sorted(RAW_DIR.rglob("*.md", recurse_symlinks=True)):
        if not p.is_file():
            continue
        raw_rel = _raw_rel(p)
        prev = lookup_file_entry(old_files, raw_rel)
        if preserve_failed and prev.get("status") == "failed":
            files[raw_rel] = {**prev, "updated_at": _now()}
            continue
        files[raw_rel] = classify_raw(p, prev)

    data = _empty_manifest()
    data["files"] = files
    if old.get("last_stop"):
        data["last_stop"] = old["last_stop"]
    save_manifest(data)
    return data


def mark_done(raw_rel: str, *, pages: int, content_hash: str) -> None:
    data = load_manifest()
    files = data.setdefault("files", {})
    raw_rel = canonical_raw_rel(raw_rel)
    status: Status = "no_actions" if pages == 0 else "done"
    files[raw_rel] = {
        "status": status,
        "content_hash": content_hash,
        "raw_path": raw_rel,
        "pages_updated": pages,
        "completed_at": _now(),
        "updated_at": _now(),
        "error": None,
    }
    data["last_stop"] = {"rel": raw_rel, "status": status, "at": _now(), "pages": pages}
    save_manifest(data)


def mark_failed(raw_rel: str, *, content_hash: str, error: str) -> None:
    data = load_manifest()
    files = data.setdefault("files", {})
    raw_rel = canonical_raw_rel(raw_rel)
    files[raw_rel] = {
        "status": "failed",
        "content_hash": content_hash,
        "raw_path": raw_rel,
        "error": str(error)[:500],
        "failed_at": _now(),
        "updated_at": _now(),
    }
    data["last_stop"] = {"rel": raw_rel, "status": "failed", "at": _now(), "error": str(error)[:200]}
    save_manifest(data)


def list_resume_targets(
    *,
    force: bool = False,
    folder: str | None = None,
    wave: str | None = None,
) -> list[tuple[str, Path]]:
    """Return (raw_rel, abs_path) for pending synthesize targets."""

    data = scan_all()
    files = data.get("files", {})
    out: list[tuple[str, Path]] = []

    for raw_rel, entry in sorted(files.items()):
        if entry.get("status") not in ("pending", "failed") and not force:
            continue
        if folder:
            prefix = folder.strip("/")
            inner = _raw_inner_path(raw_rel)
            if not inner.startswith(prefix):
                continue
        abs_path = WORKSPACE_PATH / raw_rel
        if not abs_path.is_file():
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
        out.append((raw_rel, abs_path))

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
            if e.get("status") == "pending" and _raw_inner_path(r).startswith(prefix)
        ]
        print(f"  pending under {prefix}: {len(pending)}")
