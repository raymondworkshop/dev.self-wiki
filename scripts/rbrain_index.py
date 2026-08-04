"""Build deterministic paragraph index over self-wiki/raw/ for rbrain."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config import RBRAIN_INDEX_JSON, RAW_DIR, WORKSPACE_PATH, workspace_relpath

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


def _vault_raw_rel(path: Path) -> str:
    """Path relative to RAW_DIR, always with forward slashes."""
    try:
        return str(path.relative_to(RAW_DIR)).replace("\\", "/")
    except ValueError:
        return path.name


def _workspace_raw_path(rel: str) -> str:
    return f"raw/{rel}" if not rel.startswith("raw/") else rel


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
    if not RAW_DIR.exists():
        logger.warning("RAW_DIR missing: %s", RAW_DIR)
        return []
    return sorted(p for p in RAW_DIR.rglob("*.md") if p.is_file())


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
    if not RBRAIN_INDEX_JSON.exists():
        return {"version": 1, "built_at": None, "files": {}, "paragraphs": []}
    return json.loads(RBRAIN_INDEX_JSON.read_text(encoding="utf-8"))


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
    files_meta = idx.get("files") or {}
    current = {workspace_relpath(p): file_fingerprint(p) for p in iter_raw_md_files()}
    if set(current) != set(files_meta):
        return True
    for rel, fp in current.items():
        old = files_meta.get(rel) or {}
        if old.get("mtime") != fp["mtime"] or old.get("size") != fp["size"]:
            return True
    return False


def build_index(*, force: bool = False) -> dict[str, Any]:
    existing = load_index() if RBRAIN_INDEX_JSON.exists() else None
    if existing and not force and not index_is_stale(existing):
        logger.info("rbrain index up to date: %s", RBRAIN_INDEX_JSON)
        return existing

    files_meta: dict[str, Any] = {}
    paragraphs: list[dict[str, Any]] = []
    for path in iter_raw_md_files():
        rel = workspace_relpath(path)
        files_meta[rel] = file_fingerprint(path)
        paragraphs.extend(build_paragraphs_for_file(path))

    digest = hashlib.sha256(
        json.dumps(
            [{"id": p["id"], "start_line": p["start_line"], "end_line": p["end_line"]} for p in paragraphs],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]

    index = {
        "version": 1,
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "workspace": str(WORKSPACE_PATH),
        "raw_dir": workspace_relpath(RAW_DIR) if RAW_DIR.exists() else "self-wiki/raw",
        "file_count": len(files_meta),
        "paragraph_count": len(paragraphs),
        "digest": digest,
        "files": files_meta,
        "paragraphs": paragraphs,
    }
    RBRAIN_INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    RBRAIN_INDEX_JSON.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Wrote rbrain index: %s files, %s paragraphs → %s",
        index["file_count"],
        index["paragraph_count"],
        RBRAIN_INDEX_JSON,
    )
    return index


def ensure_index(*, force: bool = False) -> dict[str, Any]:
    return build_index(force=force)


def main() -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Build rbrain paragraph index over raw/")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    idx = build_index(force=args.force)
    print(
        f"rbrain-index: {idx['file_count']} files, {idx['paragraph_count']} paragraphs "
        f"→ {workspace_relpath(RBRAIN_INDEX_JSON)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
