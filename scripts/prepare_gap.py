"""Prepare gap pending from latest discovery report."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import yaml

from compression_manifest import load_manifest, summarize_files
from config import PENDING_DIR, TWIN_PROFILE, WIKI_DIR, WORKSPACE_PATH
from skill_registry import resolve_skill

DISCOVERY_DIR = WORKSPACE_PATH / "self-wiki" / "discovery"


def _latest_discovery() -> Path | None:
    if not DISCOVERY_DIR.exists():
        return None
    files = [
        p
        for p in DISCOVERY_DIR.glob("*.md")
        if p.is_file() and not p.name.startswith("_")
    ]
    if not files:
        files = list(DISCOVERY_DIR.glob("*.md"))
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _wiki_context() -> dict:
    l1 = l2 = 0
    if not WIKI_DIR.exists():
        return {"wiki_l1": 0, "wiki_l2": 0, "pages": []}
    pages: list[str] = []
    for path in sorted(WIKI_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fm: dict = {}
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                fm = yaml.safe_load(text[3:end]) or {}
        level = int(fm.get("level", 0) or 0)
        if level >= 2:
            l2 += 1
        elif level == 1:
            l1 += 1
        pages.append(fm.get("title", path.stem))
    return {"wiki_l1": l1, "wiki_l2": l2, "pages": pages}


def _twin_principle_count() -> int:
    if not TWIN_PROFILE.exists():
        return 0
    match = re.search(r"principle_count:\s*(\d+)", TWIN_PROFILE.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else 0


def write_pending(*, provider: str | None = None) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pending_path = PENDING_DIR / f"gap-{ts}.json"
    latest = _latest_discovery()
    manifest = summarize_files(load_manifest().get("files", {}))
    wiki_ctx = _wiki_context()
    context = {
        "date": datetime.now().date().isoformat(),
        "manifest_done": manifest.get("done", 0),
        "manifest_pending": manifest.get("pending", 0),
        "wiki_l1": wiki_ctx["wiki_l1"],
        "wiki_l2": wiki_ctx["wiki_l2"],
        "wiki_pages": wiki_ctx["pages"],
        "twin_principle_count": _twin_principle_count(),
        "discovery_report": (
            str(latest.relative_to(WORKSPACE_PATH)).replace("\\", "/") if latest else None
        ),
    }
    if not latest:
        discovery_text = (
            "(No discovery report yet — infer gaps from compression samples only if provided.)"
        )
    else:
        discovery_text = latest.read_text(encoding="utf-8", errors="replace")[:12000]
    user_message = (
        f"Gap analysis {context['date']}\n\n"
        f"## Corpus context\n```json\n{json.dumps(context, indent=2, ensure_ascii=False)}\n```\n\n"
        f"## Latest discovery\n{discovery_text}\n"
    )
    out_name = f"self-wiki/gap/{context['date']}.md"
    payload = {
        "kind": "gap",
        "skill": resolve_skill("gap", "skills/gap.md"),
        "user_message": user_message,
        "output_file": out_name,
        "created_at": datetime.now().isoformat(),
    }
    pending_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return pending_path
