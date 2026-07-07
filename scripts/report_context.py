"""Shared helpers for discovery / gap / evolution report stages."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from config import TWIN_PROFILE, WIKI_DIR, WORKSPACE_PATH

REPORT_DIRS = {
    "discovery": WORKSPACE_PATH / "self-wiki" / "discovery",
    "gap": WORKSPACE_PATH / "self-wiki" / "gap",
    "evolution": WORKSPACE_PATH / "self-wiki" / "evolution",
}


def count_md(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.rglob("*.md") if p.is_file())


def latest_report(directory: Path) -> Path | None:
    if not directory.exists():
        return None
    files = [
        p
        for p in directory.glob("*.md")
        if p.is_file() and not p.name.startswith("_")
    ]
    if not files:
        files = list(directory.glob("*.md"))
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def list_reports(directory: Path) -> list[dict]:
    if not directory.exists():
        return []
    runs = []
    for path in sorted(directory.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        runs.append(
            {
                "output": str(path.relative_to(WORKSPACE_PATH)).replace("\\", "/"),
                "date": path.stem,
                "completed_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "status": "done",
            }
        )
    return runs


def twin_principle_count() -> int:
    if not TWIN_PROFILE.exists():
        return 0
    match = re.search(r"principle_count:\s*(\d+)", TWIN_PROFILE.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else 0


def wiki_summary(*, detailed_pages: bool = False) -> dict:
    l1 = l2 = shift = 0
    pages: list = []
    if not WIKI_DIR.exists():
        return {"l1": 0, "l2": 0, "type_shift": 0, "pages": pages}
    for path in sorted(WIKI_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fm: dict = {}
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                fm = yaml.safe_load(text[3:end]) or {}
        level = int(fm.get("level", 0) or 0)
        tags = fm.get("tags", [])
        if not isinstance(tags, list):
            tags = [str(tags)]
        tag_blob = " ".join(str(t) for t in tags)
        if level >= 2:
            l2 += 1
        elif level == 1:
            l1 += 1
        if "type/shift" in tag_blob:
            shift += 1
        if detailed_pages:
            pages.append(
                {
                    "title": fm.get("title", path.stem),
                    "level": level,
                    "rel": str(path.relative_to(WORKSPACE_PATH)).replace("\\", "/"),
                    "tags": tags,
                }
            )
        else:
            pages.append(fm.get("title", path.stem))
    return {"l1": l1, "l2": l2, "type_shift": shift, "pages": pages}
