"""Unified pipeline progress — all stages, resume from stop points."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from compression_manifest import (
    MANIFEST_JSON as COMPRESSION_MANIFEST_JSON,
    load_manifest as load_compression_manifest,
    scan_all as scan_compression,
    summarize_files,
)
from config import (
    AUDIT_MD,
    COMPRESSION_DIR,
    LOG_DIR,
    LOG_MD,
    TWIN_PROFILE,
    WORKSPACE_PATH,
)

PIPELINE_JSON = LOG_DIR / "pipeline_progress.json"
PROGRESS_MD = LOG_DIR / "PROGRESS.md"

StageStatus = Literal["done", "pending", "stale", "failed", "in_progress", "skipped"]

PIPELINE_ORDER = (
    "register_reference",
    "compression",
    "post_ingest",
    "discovery",
    "gap",
    "evolution",
    "audit",
)

STAGE_DIRS = {
    "discovery": WORKSPACE_PATH / "self-wiki" / "discovery",
    "gap": WORKSPACE_PATH / "self-wiki" / "gap",
    "evolution": WORKSPACE_PATH / "self-wiki" / "evolution",
}

STAGE_RESUME = {
    "register_reference": "make register-reference",
    "compression": "make compress LIMIT=50",
    "post_ingest": "make post-ingest",
    "discovery": "make discover",
    "gap": "make gap",
    "evolution": "make evolution",
    "audit": "make audit",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now().date().isoformat()


def load_pipeline() -> dict:
    if not PIPELINE_JSON.exists():
        return _empty_pipeline()
    try:
        data = json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_pipeline()
    data.setdefault("stages", {})
    data.setdefault("cycle", {})
    return data


def _empty_pipeline() -> dict:
    return {
        "version": 1,
        "updated_at": _now(),
        "cycle": {
            "status": "idle",
            "resume_stage": None,
            "resume_command": None,
            "completed_stages": [],
            "last_stop": None,
        },
        "stages": {},
    }


def save_pipeline(data: dict) -> None:
    data["updated_at"] = _now()
    PIPELINE_JSON.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _list_reports(directory: Path) -> list[dict]:
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


def _scan_register_reference() -> dict:
    sources = LOG_DIR / "sources.json"
    if not sources.exists():
        return {
            "status": "pending",
            "resume_command": STAGE_RESUME["register_reference"],
            "output": str(sources.relative_to(WORKSPACE_PATH)),
        }
    try:
        data = json.loads(sources.read_text(encoding="utf-8"))
        count = data.get("count", 0)
    except (json.JSONDecodeError, OSError):
        count = 0
    return {
        "status": "done",
        "output": str(sources.relative_to(WORKSPACE_PATH)),
        "count": count,
        "completed_at": datetime.fromtimestamp(
            sources.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
        "resume_command": STAGE_RESUME["register_reference"],
    }


def _scan_compression() -> dict:
    cm = load_compression_manifest()
    if not cm.get("files"):
        cm = scan_compression()
    summary = cm.get("summary") or summarize_files(cm.get("files", {}))
    remaining = summary.get("pending", 0) + summary.get("stale", 0) + summary.get("failed", 0)
    done = summary.get("done", 0)
    compressible = done + remaining

    if remaining == 0 and done > 0:
        status: StageStatus = "done"
    elif done > 0:
        status = "in_progress"
    else:
        status = "pending"

    resume = STAGE_RESUME["compression"]
    if remaining > 0:
        resume = f"make compress LIMIT=50  # {remaining} remaining"

    return {
        "status": status,
        "summary": summary,
        "done": done,
        "remaining": remaining,
        "compressible": compressible,
        "manifest": str(COMPRESSION_MANIFEST_JSON.relative_to(WORKSPACE_PATH)),
        "detail_report": "log/compression_progress.md",
        "last_stop": cm.get("last_stop"),
        "resume_command": resume,
    }


def _scan_post_ingest(_compression_done: int) -> dict:
    comp_files = [p for p in COMPRESSION_DIR.rglob("*.md") if p.is_file()] if COMPRESSION_DIR.exists() else []
    if not comp_files:
        return {
            "status": "skipped",
            "reason": "no compression/ digests yet",
            "resume_command": STAGE_RESUME["post_ingest"],
        }

    newest_comp = max(p.stat().st_mtime for p in comp_files)
    twin_mtime = TWIN_PROFILE.stat().st_mtime if TWIN_PROFILE.exists() else 0

    if TWIN_PROFILE.exists() and twin_mtime >= newest_comp:
        status: StageStatus = "done"
        reason = None
    else:
        status = "pending"
        reason = f"{len(comp_files)} compression file(s) — twin/index may be stale"

    return {
        "status": status,
        "reason": reason,
        "compression_files": len(comp_files),
        "twin_profile": str(TWIN_PROFILE.relative_to(WORKSPACE_PATH)),
        "resume_command": STAGE_RESUME["post_ingest"],
    }


def _scan_report_stage(stage: str, *, upstream_done: int) -> dict:
    directory = STAGE_DIRS[stage]
    runs = _list_reports(directory)
    latest = runs[0] if runs else None

    if not latest:
        status: StageStatus = "pending"
        reason = f"no report in self-wiki/{stage}/"
    elif latest.get("date") != _today():
        status = "stale"
        reason = f"latest report is {latest.get('date')} (not today)"
    else:
        status = "done"
        reason = None

    # gap needs discovery first
    if stage == "gap" and not _list_reports(STAGE_DIRS["discovery"]):
        status = "skipped"
        reason = "run discovery first"

    entry: dict[str, Any] = {
        "status": status,
        "reason": reason,
        "runs": runs[:10],
        "latest": latest,
        "resume_command": STAGE_RESUME[stage],
    }
    prev = load_pipeline().get("stages", {}).get(stage, {})
    if prev.get("status") == "failed":
        entry["status"] = "failed"
        entry["error"] = prev.get("error")
        entry["failed_at"] = prev.get("failed_at")
    return entry


def _scan_audit() -> dict:
    if not AUDIT_MD.exists():
        return {
            "status": "pending",
            "output": str(AUDIT_MD.relative_to(WORKSPACE_PATH)),
            "resume_command": STAGE_RESUME["audit"],
        }
    return {
        "status": "done",
        "output": str(AUDIT_MD.relative_to(WORKSPACE_PATH)),
        "completed_at": datetime.fromtimestamp(
            AUDIT_MD.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
        "resume_command": "make audit LINT=1",
    }


def _compute_cycle(stages: dict) -> dict:
    completed: list[str] = []
    resume_stage = None
    resume_command = None

    for name in PIPELINE_ORDER:
        st = stages.get(name, {})
        status = st.get("status")
        if status == "done":
            completed.append(name)
        elif status in ("pending", "stale", "failed", "in_progress") and resume_stage is None:
            resume_stage = name
            resume_command = st.get("resume_command") or STAGE_RESUME.get(name)

    if resume_stage is None:
        cycle_status = "complete" if completed else "idle"
    elif resume_stage == "compression" and stages.get("compression", {}).get("remaining", 0) > 0:
        cycle_status = "in_progress"
    elif resume_stage:
        cycle_status = "in_progress"
    else:
        cycle_status = "idle"

    last_stop = None
    for name in reversed(PIPELINE_ORDER):
        st = stages.get(name, {})
        if st.get("last_stop"):
            last_stop = {**st["last_stop"], "stage": name}
            break
        if name == "compression" and st.get("last_stop"):
            last_stop = {**st["last_stop"], "stage": "compression"}
            break

    old_cycle = load_pipeline().get("cycle", {})
    return {
        "status": cycle_status,
        "resume_stage": resume_stage,
        "resume_command": resume_command,
        "completed_stages": completed,
        "last_stop": last_stop or old_cycle.get("last_stop"),
    }


def refresh_all(*, rescan_compression: bool = True) -> dict:
    if rescan_compression:
        scan_compression()

    compression = _scan_compression()
    comp_done = compression.get("done", 0)

    stages = {
        "register_reference": _scan_register_reference(),
        "compression": compression,
        "post_ingest": _scan_post_ingest(comp_done),
        "discovery": _scan_report_stage("discovery", upstream_done=comp_done),
        "gap": _scan_report_stage("gap", upstream_done=comp_done),
        "evolution": _scan_report_stage("evolution", upstream_done=comp_done),
        "audit": _scan_audit(),
    }

    data = _empty_pipeline()
    old = load_pipeline()
    data["stages"] = stages
    data["cycle"] = _compute_cycle(stages)
    # preserve failed markers set by mark_stage_failed until scan clears them
    for name, prev in old.get("stages", {}).items():
        if prev.get("status") == "failed" and stages.get(name, {}).get("status") == "pending":
            stages[name]["status"] = "failed"
            stages[name]["error"] = prev.get("error")
    data["cycle"] = _compute_cycle(stages)
    save_pipeline(data)
    write_progress_md(data)
    return data


def mark_stage_done(stage: str, *, output: str | None = None, detail: dict | None = None) -> None:
    data = load_pipeline()
    stages = data.setdefault("stages", {})
    entry = stages.setdefault(stage, {})
    entry["status"] = "done"
    entry["completed_at"] = _now()
    if output:
        entry["output"] = output
    if detail:
        entry.update(detail)
    entry["last_stop"] = {"status": "done", "at": _now(), "output": output}
    data["cycle"] = _compute_cycle(stages)
    save_pipeline(data)
    write_progress_md(data)


def mark_stage_failed(stage: str, error: str) -> None:
    data = load_pipeline()
    stages = data.setdefault("stages", {})
    entry = stages.setdefault(stage, {})
    entry["status"] = "failed"
    entry["error"] = str(error)[:500]
    entry["failed_at"] = _now()
    entry["last_stop"] = {
        "status": "failed",
        "at": _now(),
        "error": str(error)[:200],
    }
    data["cycle"] = _compute_cycle(stages)
    save_pipeline(data)
    write_progress_md(data)


def mark_stage_in_progress(stage: str) -> None:
    data = load_pipeline()
    stages = data.setdefault("stages", {})
    stages.setdefault(stage, {})["status"] = "in_progress"
    stages[stage]["started_at"] = _now()
    data["cycle"] = _compute_cycle(stages)
    save_pipeline(data)


def write_progress_md(data: dict | None = None) -> Path:
    if data is None:
        data = refresh_all(rescan_compression=False)

    stages = data.get("stages", {})
    cycle = data.get("cycle", {})

    lines = [
        "# Pipeline progress",
        "",
        f"Updated: {data.get('updated_at', _now())}",
        "",
        "Machine index: `log/pipeline_progress.json`",
        "Compression detail: `log/compression_manifest.json` · `log/compression_progress.md`",
        "",
        "## Cycle",
        "",
        f"- **Status:** {cycle.get('status', 'idle')}",
    ]

    if cycle.get("resume_stage"):
        lines.append(f"- **Resume stage:** `{cycle.get('resume_stage')}`")
        lines.append(f"- **Resume command:** `{cycle.get('resume_command')}`")
    if cycle.get("completed_stages"):
        lines.append(f"- **Completed:** {', '.join(cycle.get('completed_stages', []))}")
    if cycle.get("last_stop"):
        ls = cycle["last_stop"]
        lines.extend(
            [
                "",
                "### Last stop",
                "",
                f"- **Stage:** {ls.get('stage', ls.get('rel', '?'))}",
                f"- **Status:** {ls.get('status')}",
                f"- **At:** {ls.get('at')}",
            ]
        )
        if ls.get("rel"):
            lines.append(f"- **File:** `{ls.get('rel')}`")
        if ls.get("error"):
            lines.append(f"- **Error:** {ls.get('error')}")

    lines.extend(["", "## Stages", ""])
    lines.append("| Stage | Status | Done / detail | Resume |")
    lines.append("|-------|--------|---------------|--------|")

    for name in PIPELINE_ORDER:
        st = stages.get(name, {})
        status = st.get("status", "pending")
        if name == "compression":
            detail = f"{st.get('done', 0)}/{st.get('compressible', 0)} files"
            if st.get("remaining"):
                detail += f" ({st.get('remaining')} left)"
        elif name == "register_reference":
            detail = f"{st.get('count', '—')} twitter entries" if status == "done" else "—"
        elif name in ("discovery", "gap", "evolution"):
            latest = st.get("latest")
            detail = latest.get("output", "—") if latest else st.get("reason", "—")
        else:
            detail = st.get("reason") or st.get("output") or "—"
        resume = f"`{st.get('resume_command', '')}`" if status != "done" else "—"
        mark = "x" if status == "done" else " "
        lines.append(f"| [{mark}] {name} | {status} | {detail} | {resume} |")

    lines.extend(["", "## Resume cheatsheet", "", "```bash", "make progress              # refresh + print",])

    if cycle.get("resume_command"):
        lines.append(cycle["resume_command"])
    lines.extend(
        [
            "make compress LIMIT=50",
            "make compress FOLDER=origin-apple-notes LIMIT=30",
            "make post-ingest",
            "make discover && make gap && make evolution",
            "make audit",
            "```",
            "",
        ]
    )

    # Compression file lists delegated
    cm = load_compression_manifest()
    if cm.get("files"):
        summary = cm.get("summary", {})
        lines.extend(
            [
                "## Compression files (summary)",
                "",
                f"- done: {summary.get('done', 0)} · pending: {summary.get('pending', 0)} · "
                f"stale: {summary.get('stale', 0)} · failed: {summary.get('failed', 0)}",
                "- Full checklists: [compression_progress.md](compression_progress.md)",
                "",
            ]
        )

    PROGRESS_MD.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_MD.write_text("\n".join(lines), encoding="utf-8")
    return PROGRESS_MD


def print_status() -> dict:
    data = refresh_all()
    cycle = data["cycle"]
    stages = data["stages"]

    print("Pipeline progress")
    print("=" * 40)
    for name in PIPELINE_ORDER:
        st = stages.get(name, {})
        status = st.get("status", "pending")
        icon = {"done": "✓", "failed": "!", "in_progress": "…"}.get(status, "○")
        extra = ""
        if name == "compression":
            extra = f"  ({st.get('done', 0)}/{st.get('compressible', 0)})"
        print(f"  [{icon}] {name:<22} {status}{extra}")

    print()
    if cycle.get("resume_stage"):
        print(f"Resume: {cycle.get('resume_command')}")
    if cycle.get("last_stop"):
        ls = cycle["last_stop"]
        print(f"Last stop: [{ls.get('status')}] {ls.get('stage', '')} {ls.get('rel', '')}")
    print(f"\nReport: {PROGRESS_MD.relative_to(WORKSPACE_PATH)}")
    return data
