#!/usr/bin/env python3
"""Catalog twitter raw files into log/sources.json (no LLM)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from config import LOG_DIR, RAW_DIR, WORKSPACE_PATH

SOURCES_JSON = LOG_DIR / "sources.json"
TWITTER_DIR = RAW_DIR / "twitter"


def _rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE_PATH)).replace("\\", "/")


def _parse_tweet_blocks(text: str, source_file: str) -> list[dict]:
    entries: list[dict] = []
    blocks = re.split(r"\n---\n", text)
    for block in blocks:
        block = block.strip()
        if not block or block.startswith("# Twitter"):
            continue
        header = re.search(r"^##\s+tweet\s+(\d+)", block, re.MULTILINE)
        url_match = re.search(r"URL:\s*(https?://\S+)", block)
        if not header:
            continue
        tweet_id = header.group(1)
        url = url_match.group(1) if url_match else f"https://twitter.com/i/web/status/{tweet_id}"
        body_lines = []
        for line in block.splitlines():
            if line.startswith("## tweet") or line.startswith("- URL:"):
                continue
            body_lines.append(line)
        excerpt = "\n".join(body_lines).strip()
        if len(excerpt) > 280:
            excerpt = excerpt[:277] + "..."
        entries.append(
            {
                "id": tweet_id,
                "url": url,
                "excerpt": excerpt,
                "source_file": source_file,
                "type": "external",
            }
        )
    return entries


def _parse_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = _rel(path)
    if "tweet" in text and "## tweet" in text:
        return _parse_tweet_blocks(text, rel)
    title = path.stem.replace("-", " ").title()
    return [
        {
            "id": path.stem,
            "url": None,
            "excerpt": text[:280] + ("..." if len(text) > 280 else ""),
            "source_file": rel,
            "type": "external",
            "title": title,
        }
    ]


def build_catalog() -> dict:
    entries: list[dict] = []
    if TWITTER_DIR.exists():
        for path in sorted(TWITTER_DIR.rglob("*.md")):
            if not path.is_file():
                continue
            entries.extend(_parse_file(path))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_type": "twitter_likes",
        "count": len(entries),
        "entries": entries,
    }


def register_references(*, dry_run: bool = False) -> Path:
    catalog = build_catalog()
    if dry_run:
        print(json.dumps({"count": catalog["count"], "sample": catalog["entries"][:3]}, indent=2, ensure_ascii=False))
        return SOURCES_JSON
    SOURCES_JSON.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_JSON.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return SOURCES_JSON


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Register twitter raw → log/sources.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    path = register_references(dry_run=args.dry_run)
    if not args.dry_run:
        catalog = json.loads(path.read_text(encoding="utf-8"))
        print(f"Wrote {catalog['count']} entries to {path.relative_to(WORKSPACE_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
