"""Prepare gap pending from latest discovery report."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from wiki_synth_manifest import load_manifest, summarize_files
from config import PENDING_DIR, WORKSPACE_PATH
from report_context import REPORT_DIRS, latest_report, twin_principle_count, wiki_summary
from skill_registry import resolve_skill
from pending_builder import write_skill_pending_json


def write_pending(*, provider: str | None = None) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pending_name = f"gap-{ts}.json"
    latest = latest_report(REPORT_DIRS["discovery"])
    manifest = summarize_files(load_manifest().get("files", {}))
    wiki_ctx = wiki_summary()
    context = {
        "date": datetime.now().date().isoformat(),
        "manifest_done": manifest.get("done", 0),
        "manifest_pending": manifest.get("pending", 0),
        "wiki_l1": wiki_ctx["l1"],
        "wiki_l2": wiki_ctx["l2"],
        "wiki_pages": wiki_ctx["pages"],
        "twin_principle_count": twin_principle_count(),
        "discovery_report": (
            str(latest.relative_to(WORKSPACE_PATH)).replace("\\", "/") if latest else None
        ),
    }
    if not latest:
        discovery_text = (
            "(No discovery report yet — infer gaps from raw/wiki context in the pack.)"
        )
    else:
        discovery_text = latest.read_text(encoding="utf-8", errors="replace")[:12000]
    user_message = (
        f"Gap analysis {context['date']}\n\n"
        f"## Corpus context\n```json\n{json.dumps(context, indent=2, ensure_ascii=False)}\n```\n\n"
        f"## Latest discovery\n{discovery_text}\n"
    )
    out_name = f"self-wiki/gap/{context['date']}.md"
    pending_path = write_skill_pending_json(
        pending_dir=PENDING_DIR,
        pending_name=pending_name,
        kind="gap",
        skill=resolve_skill("gap", "skills/gap.md"),
        user_message=user_message,
        output_file=out_name,
        created_at=datetime.now().isoformat(),
    )
    return pending_path
