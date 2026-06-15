"""Prepare evolution evidence pack (mostly deterministic)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import yaml

from compression_manifest import load_manifest, summarize_files
from config import COMPRESSION_DIR, PENDING_DIR, TWIN_PROFILE, WIKI_DIR, WORKSPACE_PATH
from llm_provider import provider_name

EVOLUTION_DIR = WORKSPACE_PATH / "self-wiki" / "evolution"
GAP_DIR = WORKSPACE_PATH / "self-wiki" / "gap"
DISCOVERY_DIR = WORKSPACE_PATH / "self-wiki" / "discovery"


def _count_md(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.rglob("*.md") if p.is_file())


def _latest_report(directory: Path) -> Path | None:
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


def _wiki_breakdown() -> dict:
    l1 = l2 = shift = 0
    pages: list[dict] = []
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
        pages.append(
            {
                "title": fm.get("title", path.stem),
                "level": level,
                "rel": str(path.relative_to(WORKSPACE_PATH)).replace("\\", "/"),
                "tags": tags,
            }
        )
    return {"l1": l1, "l2": l2, "type_shift": shift, "pages": pages}


def _twin_principle_count() -> int:
    if not TWIN_PROFILE.exists():
        return 0
    match = re.search(r"principle_count:\s*(\d+)", TWIN_PROFILE.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else 0


def _prior_evolution(before: str) -> Path | None:
    if not EVOLUTION_DIR.exists():
        return None
    for path in sorted(EVOLUTION_DIR.glob("*.md"), reverse=True):
        if path.name.startswith("_"):
            continue
        if path.stem < before:
            return path
    return None


def build_metrics_pack() -> dict:
    manifest = summarize_files(load_manifest().get("files", {}))
    wiki = _wiki_breakdown()
    date = datetime.now().date().isoformat()
    prior = _prior_evolution(date)
    latest_gap = _latest_report(GAP_DIR)
    latest_discovery = _latest_report(DISCOVERY_DIR)
    return {
        "date": date,
        "compression_md_files": _count_md(COMPRESSION_DIR),
        "manifest": manifest,
        "wiki_total": _count_md(WIKI_DIR),
        "wiki_l1": wiki["l1"],
        "wiki_l2": wiki["l2"],
        "type_shift_pages": wiki["type_shift"],
        "wiki_pages": wiki["pages"],
        "twin_principle_count": _twin_principle_count(),
        "discovery_report": (
            str(latest_discovery.relative_to(WORKSPACE_PATH)).replace("\\", "/")
            if latest_discovery
            else None
        ),
        "gap_report": (
            str(latest_gap.relative_to(WORKSPACE_PATH)).replace("\\", "/")
            if latest_gap
            else None
        ),
        "prior_evolution": (
            str(prior.relative_to(WORKSPACE_PATH)).replace("\\", "/") if prior else None
        ),
        "is_bootstrap": prior is None,
    }


def write_pending(*, provider: str | None = None) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pending_path = PENDING_DIR / f"evolution-{ts}.json"
    metrics = build_metrics_pack()
    user_message = (
        f"Evolution snapshot {metrics['date']}\n"
        f"Provider hint: {provider_name(provider)}\n\n"
        f"## Deterministic metrics\n```json\n{json.dumps(metrics, indent=2, ensure_ascii=False)}\n```\n"
    )
    if metrics.get("prior_evolution"):
        prior_path = WORKSPACE_PATH / metrics["prior_evolution"]
        prior_text = prior_path.read_text(encoding="utf-8", errors="replace")[:6000]
        user_message += f"\n## Prior evolution (for Δ)\n{prior_text}\n"
    if metrics.get("gap_report"):
        gap_path = WORKSPACE_PATH / metrics["gap_report"]
        gap_text = gap_path.read_text(encoding="utf-8", errors="replace")[:4000]
        user_message += f"\n## Latest gap (learning strategy source)\n{gap_text}\n"
    out_name = f"self-wiki/evolution/{metrics['date']}.md"
    payload = {
        "kind": "evolution",
        "skill": "skills/evolution.md",
        "user_message": user_message,
        "output_file": out_name,
        "created_at": datetime.now().isoformat(),
    }
    pending_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return pending_path
