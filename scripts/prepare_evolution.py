"""Prepare evolution evidence pack (mostly deterministic)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config import PENDING_DIR, RAW_DIR, WIKI_DIR, WORKSPACE_PATH
from wiki_synth_manifest import load_manifest, summarize_files
from llm_provider import provider_name
from report_context import (
    REPORT_DIRS,
    count_md,
    latest_report,
    twin_principle_count,
    wiki_summary,
)
from skill_registry import resolve_skill

EVOLUTION_DIR = REPORT_DIRS["evolution"]


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
    manifest_files = load_manifest().get("files", {})
    manifest = summarize_files(manifest_files)
    wiki = wiki_summary(detailed_pages=True)
    date = datetime.now().date().isoformat()
    prior = _prior_evolution(date)
    latest_gap = latest_report(REPORT_DIRS["gap"])
    latest_discovery = latest_report(REPORT_DIRS["discovery"])
    discovery_count = count_md(REPORT_DIRS["discovery"])
    gap_count = count_md(REPORT_DIRS["gap"])
    return {
        "date": date,
        "raw_md_files": count_md(RAW_DIR),
        "wiki_synth_manifest": {
            "tracked": len(manifest_files),
            **manifest,
        },
        "manifest": manifest,
        "wiki_total": count_md(WIKI_DIR),
        "wiki_l1": wiki["l1"],
        "wiki_l2": wiki["l2"],
        "type_shift_pages": wiki["type_shift"],
        "wiki_pages": wiki["pages"],
        "twin_principle_count": twin_principle_count(),
        "discovery_reports": discovery_count,
        "gap_reports": gap_count,
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
        "pipeline": "raw → wiki-synthesize → wiki → discovery → gap → evolution; ingest → twin",
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
        "skill": resolve_skill("evolution", "skills/evolution.md"),
        "user_message": user_message,
        "output_file": out_name,
        "created_at": datetime.now().isoformat(),
    }
    pending_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return pending_path
