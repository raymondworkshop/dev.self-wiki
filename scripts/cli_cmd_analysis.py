"""Analysis report CLI command handlers (discover/gap/evolution)."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from composer_policy import reject_python_llm_ingest
from llm_provider import provider_for_role
from log_utils import append_log
from pipeline_progress import (
    mark_stage_done,
    mark_stage_failed,
    mark_stage_in_progress,
    refresh_all,
)
from prepare_discover import write_pending as write_discover_pending
from prepare_evolution import write_pending as write_evolution_pending
from prepare_gap import write_pending as write_gap_pending
from run_skill import run_skill_from_pending

_STAGE_CONFIG: dict[str, tuple[str, str, Callable[..., Path]]] = {
    "discover": ("discovery", "discover", write_discover_pending),
    "gap": ("gap", "gap", write_gap_pending),
    "evolution": ("evolution", "evolution", write_evolution_pending),
}


def _run_report_stage(command: str, args: argparse.Namespace) -> int:
    role, progress_stage, write_pending = _STAGE_CONFIG[command]
    provider = provider_for_role(role, args.provider)
    reject_python_llm_ingest(context=command, provider=provider)
    mark_stage_in_progress(progress_stage)
    try:
        pending = write_pending(provider=provider)
        result = run_skill_from_pending(pending, provider=provider)
        append_log(command, f"{progress_stage} report via {pending.name}")
        mark_stage_done(progress_stage, output=result.get("output_path"))
        refresh_all()
    except Exception as exc:
        mark_stage_failed(progress_stage, str(exc))
        raise
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    return _run_report_stage("discover", args)


def cmd_gap(args: argparse.Namespace) -> int:
    return _run_report_stage("gap", args)


def cmd_evolution(args: argparse.Namespace) -> int:
    return _run_report_stage("evolution", args)
