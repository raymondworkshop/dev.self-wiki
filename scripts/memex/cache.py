"""Persist and load memex graph cache."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import LOG_DIR

MEMEX_DIR = LOG_DIR / "memex"
GRAPH_PATH = MEMEX_DIR / "graph.json"
STAMP_PATH = MEMEX_DIR / ".stamp"
SOURCE_STAMPS_PATH = MEMEX_DIR / "source-stamps.json"


def write_memex_cache(ctx: dict[str, Any]) -> Path:
    MEMEX_DIR.mkdir(parents=True, exist_ok=True)
    serializable = {
        "stats": ctx.get("stats", {}),
        "backlinks": ctx.get("backlinks", {}),
        "typed_backlinks": ctx.get("typed_backlinks", {}),
        "backlink_counts": ctx.get("backlink_counts", {}),
        "unlinked_mentions": ctx.get("unlinked_mentions", {}),
        "topic_pages": ctx.get("topic_pages", {}),
        "page_topics": ctx.get("page_topics", {}),
        "layer_pages": ctx.get("layer_pages", {}),
        "layer_hubs": ctx.get("layer_hubs", {}),
        "registry": ctx.get("registry", {}),
        "url_registry": ctx.get("url_registry", {}),
    }
    GRAPH_PATH.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    STAMP_PATH.write_text("memex\n", encoding="utf-8")
    return GRAPH_PATH


def load_memex_cache() -> dict[str, Any] | None:
    if not GRAPH_PATH.exists():
        return None
    try:
        return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
