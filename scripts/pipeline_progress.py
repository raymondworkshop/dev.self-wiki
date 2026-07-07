"""Unified pipeline progress — all stages, resume from stop points."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from config import (
    AUDIT_MD,
    LOG_DIR,
    LOG_MD,
    RAW_DIR,
    TWIN_PROFILE,
    WIKI_DIR,
    WORKSPACE_PATH,
)
from memex.cache import STAMP_PATH
from wiki_synth_manifest import MANIFEST_JSON, load_manifest, scan_all, summarize_files
from report_context import REPORT_DIRS, list_reports

PIPELINE_JSON = LOG_DIR / "pipeline_progress.json"
PROGRESS_MD = LOG_DIR / "PROGRESS.md"

StageStatus = Literal["done", "pending", "stale", "failed", "in_progress", "skipped"]

PIPELINE_ORDER = (
    "register_reference",
    "wiki_synthesize",
    "discovery",
    "gap",
    "evolution",
    "ingest",
    "audit",
)

STAGE_DIRS = REPORT_DIRS

STAGE_RESUME = {
    "register_reference": "make register-reference",
    "wiki_synthesize": "make wiki-synthesize LIMIT=20",
    "ingest": "make ingest",
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


def _scan_wiki_synthesize() -> dict:
    manifest = load_manifest()
    if not manifest.get("files"):
        scan_all()
        manifest = load_manifest()
    summary = summarize_files(manifest.get("files", {}))
    remaining = summary.get("pending", 0) + summary.get("failed", 0)
    done = summary.get("done", 0) + summary.get("no_actions", 0)
    total = done + remaining + summary.get("skipped", 0)

    if remaining == 0 and done > 0:
        status: StageStatus = "done"
    elif done > 0 or remaining > 0:
        status = "in_progress"
    else:
        status = "pending"

    resume = STAGE_RESUME["wiki_synthesize"]
    if remaining > 0:
        resume = f"make wiki-synthesize LIMIT=20  # {remaining} pending/failed"

    return {
        "status": status,
        "summary": summary,
        "done": done,
        "remaining": remaining,
        "total": total,
        "manifest": str(MANIFEST_JSON.relative_to(WORKSPACE_PATH)),
        "last_stop": manifest.get("last_stop"),
        "resume_command": resume,
    }


def _newest_vault_mtime() -> float:
    newest = 0.0
    for root in (RAW_DIR, WIKI_DIR, WORKSPACE_PATH / "self-wiki" / "twin"):
        if not root.exists():
            continue
        for path in root.rglob("*.md", recurse_symlinks=True):
            try:
                newest = max(newest, path.stat().st_mtime)
            except OSError:
                continue
    return newest


def _scan_ingest() -> dict:
    stamp_mtime = STAMP_PATH.stat().st_mtime if STAMP_PATH.exists() else 0.0
    newest = _newest_vault_mtime()
    twin_mtime = TWIN_PROFILE.stat().st_mtime if TWIN_PROFILE.exists() else 0.0

    if stamp_mtime >= newest and stamp_mtime > 0 and twin_mtime >= stamp_mtime:
        status: StageStatus = "done"
        reason = None
    else:
        status = "pending"
        reason = "vault changed since last memex ingest — run make ingest"

    return {
        "status": status,
        "reason": reason,
        "memex_stamp": str(STAMP_PATH.relative_to(WORKSPACE_PATH)) if STAMP_PATH.exists() else None,
        "twin_profile": str(TWIN_PROFILE.relative_to(WORKSPACE_PATH)),
        "resume_command": STAGE_RESUME["ingest"],
    }


def _scan_report_stage(stage: str) -> dict:
    directory = STAGE_DIRS[stage]
    runs = list_reports(directory)
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

    if stage == "gap" and not list_reports(STAGE_DIRS["discovery"]):
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

    old_cycle = load_pipeline().get("cycle", {})
    return {
        "status": cycle_status,
        "resume_stage": resume_stage,
        "resume_command": resume_command,
        "completed_stages": completed,
        "last_stop": last_stop or old_cycle.get("last_stop"),
    }


def refresh_all(*, rescan_wiki_synth: bool = True) -> dict:
    if rescan_wiki_synth:
        scan_all()

    stages = {
        "register_reference": _scan_register_reference(),
        "wiki_synthesize": _scan_wiki_synthesize(),
        "ingest": _scan_ingest(),
        "discovery": _scan_report_stage("discovery"),
        "gap": _scan_report_stage("gap"),
        "evolution": _scan_report_stage("evolution"),
        "audit": _scan_audit(),
    }

    data = _empty_pipeline()
    old = load_pipeline()
    data["stages"] = stages
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
        data = refresh_all(rescan_wiki_synth=False)

    stages = data.get("stages", {})
    cycle = data.get("cycle", {})

    lines = [
        "# Pipeline progress",
        "",
        f"Updated: {data.get('updated_at', _now())}",
        "",
        "Machine index: `log/pipeline_progress.json`",
        "Wiki-synthesize detail: `log/wiki_synth_manifest.json`",
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
        if name == "wiki_synthesize":
            detail = f"{st.get('done', 0)}/{st.get('total', 0)} raw files"
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

    lines.extend(
        [
            "",
            "## Resume cheatsheet",
            "",
            "```bash",
            "make progress              # refresh + print",
        ]
    )

    if cycle.get("resume_command"):
        lines.append(cycle["resume_command"])
    lines.extend(
        [
            "make wiki-synthesize LIMIT=20",
            "make wiki-synthesize FOLDER=origin-apple-notes LIMIT=30",
            "make ingest",
            "make discover && make gap && make evolution",
            "make audit",
            "```",
            "",
        ]
    )

    manifest = load_manifest()
    if manifest.get("files"):
        summary = manifest.get("summary", {})
        lines.extend(
            [
                "## Wiki-synthesize (summary)",
                "",
                f"- done: {summary.get('done', 0)} · no_actions: {summary.get('no_actions', 0)} · "
                f"pending: {summary.get('pending', 0)} · failed: {summary.get('failed', 0)}",
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
        if name == "wiki_synthesize":
            extra = f"  ({st.get('done', 0)}/{st.get('total', 0)})"
        print(f"  [{icon}] {name:<22} {status}{extra}")

    print()
    if cycle.get("resume_stage"):
        print(f"Resume: {cycle.get('resume_command')}")
    if cycle.get("last_stop"):
        ls = cycle["last_stop"]
        print(f"Last stop: [{ls.get('status')}] {ls.get('stage', '')} {ls.get('rel', '')}")
    print(f"\nReport: {PROGRESS_MD.relative_to(WORKSPACE_PATH)}")
    return data
