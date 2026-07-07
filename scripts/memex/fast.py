"""Incremental memex rebuild helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from memex.cache import MEMEX_DIR, SOURCE_STAMPS_PATH, STAMP_PATH
from memex.resolve import normalize_url
from memex.sources import VAULT_DIR, collect_vault_pages


def _file_stamp(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def vault_is_stale() -> bool:
    if not STAMP_PATH.exists():
        return True
    stamp_mtime = _file_stamp(STAMP_PATH)
    for path in VAULT_DIR.rglob("*.md", recurse_symlinks=True):
        if "pending" in path.parts or ".obsidian" in path.parts:
            continue
        if _file_stamp(path) > stamp_mtime:
            return True
    return False


def collect_affected_urls(ctx: dict[str, Any], changed_urls: set[str]) -> set[str]:
    backlinks = ctx.get("backlinks", {})
    affected = set(changed_urls)
    for url in changed_urls:
        for target_url, items in backlinks.items():
            if any(normalize_url(item["url"]) == url for item in items):
                affected.add(target_url)
        for item in backlinks.get(url, []):
            affected.add(normalize_url(item["url"]))
    return affected


def ingest_fast_skip() -> bool:
    return os.environ.get("FAST", "").strip() in {"1", "true", "yes"} and not vault_is_stale()


def write_source_stamps(pages: list) -> None:
    MEMEX_DIR.mkdir(parents=True, exist_ok=True)
    stamps = {p.rel: _file_stamp(p.path) for p in pages}
    SOURCE_STAMPS_PATH.write_text(json.dumps(stamps, indent=2), encoding="utf-8")
