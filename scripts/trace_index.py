"""Build deterministic paragraph index over self-wiki/raw/ for trace."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from config import TRACE_INDEX_JSON, RAW_DIR, WORKSPACE_PATH, workspace_relpath

logger = logging.getLogger(__name__)

LONG_PARA_LINE_LIMIT = 40


def _kind_for_rel(rel: str) -> str:
    if rel.startswith("twitter/") or "/twitter/" in rel:
        return "twitter"
    if rel.startswith("origin-apple-notes/") or "apple-notes" in rel:
        return "apple-notes"
    if rel.startswith("_posts/") or rel.startswith("new-apple-notes/"):
        return "post"
    return "raw"


def _is_generated_raw(rel: str) -> bool:
    """Skip LLM/pipeline outputs under raw/qa/ — not proprietary source notes."""
    parts = rel.replace("\\", "/").strip("/").split("/")
    return "qa" in parts


def _path_preference_key(rel: str) -> tuple:
    """Lower is better. Prefer vault-local paths over myblog `_posts/` mirrors."""
    rel = rel.replace("\\", "/").strip("/")
    under_posts = 1 if rel.startswith("_posts/") else 0
    return (under_posts, len(rel.split("/")), rel)


def _file_content_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _vault_raw_rel(path: Path) -> str:
    """Path relative to RAW_DIR, always with forward slashes."""
    path = Path(path)
    raw = Path(RAW_DIR)
    for base, candidate in ((raw, path), (raw.resolve(), path.resolve())):
        try:
            return str(candidate.relative_to(base)).replace("\\", "/")
        except (ValueError, OSError):
            continue
    return path.name


def _workspace_raw_path(rel: str) -> str:
    return f"raw/{rel}" if not rel.startswith("raw/") else rel


def _index_file_key(path: Path) -> str:
    """Stable files-meta key: self-wiki/raw/<path-relative-to-RAW_DIR>."""
    return f"self-wiki/raw/{_vault_raw_rel(path)}"


def split_paragraphs(content: str) -> list[tuple[int, int, str]]:
    """Return (start_line, end_line, text) 1-indexed inclusive line ranges."""
    lines = content.splitlines()
    if not lines:
        return []

    blocks: list[tuple[int, int, str]] = []
    buf: list[str] = []
    start: int | None = None

    def flush() -> None:
        nonlocal buf, start
        if start is None or not buf:
            buf = []
            start = None
            return
        text = "\n".join(buf).strip()
        if text:
            end = start + len(buf) - 1
            # Split very long blocks into windows
            if len(buf) > LONG_PARA_LINE_LIMIT:
                for i in range(0, len(buf), LONG_PARA_LINE_LIMIT):
                    chunk = buf[i : i + LONG_PARA_LINE_LIMIT]
                    chunk_text = "\n".join(chunk).strip()
                    if not chunk_text:
                        continue
                    c_start = start + i
                    c_end = c_start + len(chunk) - 1
                    blocks.append((c_start, c_end, chunk_text))
            else:
                blocks.append((start, end, text))
        buf = []
        start = None

    for i, line in enumerate(lines, start=1):
        if not line.strip():
            flush()
            continue
        if start is None:
            start = i
        buf.append(line)
    flush()
    return blocks


def iter_raw_md_files() -> list[Path]:
    """List raw/*.md including symlink dirs; skip raw/qa/; drop identical content copies.

    ``raw/_posts`` often mirrors files also present under ``raw/twitter`` (same bytes,
    different paths). Prefer the non-``_posts/`` path when digests collide.
    """
    if not RAW_DIR.exists():
        logger.warning("RAW_DIR missing: %s", RAW_DIR)
        return []
    candidates: list[Path] = []
    seen_dirs: set[Path] = set()
    # Path.rglob does not follow directory symlinks; os.walk(followlinks=True) does.
    for root, dirnames, filenames in os.walk(RAW_DIR, followlinks=True):
        root_path = Path(root)
        try:
            real = root_path.resolve()
        except OSError:
            dirnames[:] = []
            continue
        if real in seen_dirs:
            dirnames[:] = []
            continue
        seen_dirs.add(real)
        for name in filenames:
            if not name.endswith(".md"):
                continue
            path = root_path / name
            if not path.is_file():
                continue
            if _is_generated_raw(_vault_raw_rel(path)):
                continue
            candidates.append(path)

    # Content-identical duplicates (e.g. raw/twitter/* vs raw/_posts/twitter/*).
    best_by_digest: dict[str, Path] = {}
    for path in candidates:
        try:
            digest = _file_content_digest(path)
        except OSError:
            continue
        rel = _vault_raw_rel(path)
        prev = best_by_digest.get(digest)
        if prev is None or _path_preference_key(rel) < _path_preference_key(
            _vault_raw_rel(prev)
        ):
            best_by_digest[digest] = path

    dropped = len(candidates) - len(best_by_digest)
    if dropped:
        logger.info(
            "trace index: skipped %s duplicate file(s) (identical content)",
            dropped,
        )
    return sorted(best_by_digest.values())


def file_fingerprint(path: Path) -> dict[str, Any]:
    st = path.stat()
    return {"mtime": st.st_mtime_ns, "size": st.st_size}


def build_paragraphs_for_file(path: Path) -> list[dict[str, Any]]:
    rel = _vault_raw_rel(path)
    ws_path = _workspace_raw_path(rel)
    content = path.read_text(encoding="utf-8", errors="replace")
    kind = _kind_for_rel(rel)
    units: list[dict[str, Any]] = []
    for idx, (start, end, text) in enumerate(split_paragraphs(content), start=1):
        units.append(
            {
                "id": f"{ws_path}#p{idx}",
                "path": ws_path,
                "file": path.name,
                "para": idx,
                "start_line": start,
                "end_line": end,
                "text": text,
                "kind": kind,
            }
        )
    return units


def load_index() -> dict[str, Any]:
    if not TRACE_INDEX_JSON.exists():
        return {"version": 1, "built_at": None, "files": {}, "paragraphs": []}
    return json.loads(TRACE_INDEX_JSON.read_text(encoding="utf-8"))


def get_paragraph(para_id: str, index: dict[str, Any] | None = None) -> dict[str, Any] | None:
    idx = index if index is not None else load_index()
    for p in idx.get("paragraphs") or []:
        if p.get("id") == para_id:
            return p
    # Also accept path#pN without raw/ prefix variants
    for p in idx.get("paragraphs") or []:
        if p.get("id", "").endswith(para_id) or para_id.endswith(p.get("id", "")):
            return p
    return None


def index_is_stale(index: dict[str, Any] | None = None) -> bool:
    idx = index if index is not None else load_index()
    current = {_index_file_key(p): file_fingerprint(p) for p in iter_raw_md_files()}
    return _files_meta_stale(idx.get("files") or {}, current)


def _files_meta_stale(
    files_meta: dict[str, Any], current: dict[str, dict[str, Any]]
) -> bool:
    if set(current) != set(files_meta):
        return True
    for rel, fp in current.items():
        old = files_meta.get(rel) or {}
        if old.get("mtime") != fp["mtime"] or old.get("size") != fp["size"]:
            return True
    return False


def _paragraphs_by_path(paragraphs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for para in paragraphs:
        grouped.setdefault(para.get("path") or "", []).append(para)
    return grouped


def _fingerprint_unchanged(old: dict[str, Any] | None, new: dict[str, Any]) -> bool:
    if not old:
        return False
    return old.get("mtime") == new.get("mtime") and old.get("size") == new.get("size")


def _write_index(files_meta: dict[str, Any], paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    digest = hashlib.sha256(
        json.dumps(
            [
                {"id": p["id"], "start_line": p["start_line"], "end_line": p["end_line"]}
                for p in paragraphs
            ],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]

    try:
        raw_dir_rel = workspace_relpath(RAW_DIR) if RAW_DIR.exists() else "self-wiki/raw"
    except ValueError:
        raw_dir_rel = "self-wiki/raw"

    index = {
        "version": 1,
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "workspace": str(WORKSPACE_PATH),
        "raw_dir": raw_dir_rel,
        "file_count": len(files_meta),
        "paragraph_count": len(paragraphs),
        "digest": digest,
        "files": files_meta,
        "paragraphs": paragraphs,
    }
    TRACE_INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    TRACE_INDEX_JSON.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Wrote trace index: %s files, %s paragraphs → %s",
        index["file_count"],
        index["paragraph_count"],
        TRACE_INDEX_JSON,
    )
    return index


def _build_index_full(paths: list[Path]) -> dict[str, Any]:
    files_meta: dict[str, Any] = {}
    paragraphs: list[dict[str, Any]] = []
    for path in paths:
        files_meta[_index_file_key(path)] = file_fingerprint(path)
        paragraphs.extend(build_paragraphs_for_file(path))
    return _write_index(files_meta, paragraphs)


def _build_index_incremental(
    paths: list[Path],
    existing: dict[str, Any],
    *,
    current_fps: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Reuse unchanged file paragraphs; rebuild only added/changed; drop deleted."""
    old_files = existing.get("files") or {}
    old_by_path = _paragraphs_by_path(existing.get("paragraphs") or [])

    if current_fps is None:
        current_fps = {_index_file_key(path): file_fingerprint(path) for path in paths}
    path_by_key = {_index_file_key(path): path for path in paths}

    removed = len(set(old_files) - set(current_fps))
    files_meta: dict[str, Any] = {}
    paragraphs: list[dict[str, Any]] = []
    added = changed = reused = rebuilt_missing = 0

    for key in sorted(current_fps):
        path = path_by_key[key]
        fp = current_fps[key]
        files_meta[key] = fp
        para_path = _workspace_raw_path(_vault_raw_rel(path))
        if _fingerprint_unchanged(old_files.get(key), fp):
            kept = old_by_path.get(para_path) or []
            if kept:
                paragraphs.extend(kept)
                reused += 1
                continue
            rebuilt_missing += 1
        elif key not in old_files:
            added += 1
        else:
            changed += 1
        paragraphs.extend(build_paragraphs_for_file(path))

    logger.info(
        "trace index incremental: +%s ~%s -%s reused=%s rebuilt_missing=%s",
        added,
        changed,
        removed,
        reused,
        rebuilt_missing,
    )
    return _write_index(files_meta, paragraphs)


def build_index(*, force: bool = False) -> dict[str, Any]:
    existing = load_index() if TRACE_INDEX_JSON.exists() else None
    paths = iter_raw_md_files()
    current_fps = {_index_file_key(path): file_fingerprint(path) for path in paths}

    if (
        existing
        and not force
        and not _files_meta_stale(existing.get("files") or {}, current_fps)
    ):
        logger.info("trace index up to date: %s", TRACE_INDEX_JSON)
        return existing

    can_incremental = bool(
        existing
        and existing.get("files")
        and isinstance(existing.get("paragraphs"), list)
        and not force
    )
    if can_incremental:
        return _build_index_incremental(paths, existing, current_fps=current_fps)
    if force:
        logger.info("trace index full rebuild (--force)")
    return _build_index_full(paths)


def ensure_index(*, force: bool = False) -> dict[str, Any]:
    return build_index(force=force)


def main() -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Build trace paragraph index over raw/")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    idx = build_index(force=args.force)
    print(
        f"trace-index: {idx['file_count']} files, {idx['paragraph_count']} paragraphs "
        f"→ {workspace_relpath(TRACE_INDEX_JSON)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
