"""Analysis report CLI command handlers (discover/gap/evolution)."""

from __future__ import annotations

import argparse
import logging

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

logger = logging.getLogger(__name__)


def cmd_discover(args: argparse.Namespace) -> int:
    provider = provider_for_role("discovery", args.provider)
    reject_python_llm_ingest(context="discover", provider=provider)
    mark_stage_in_progress("discovery")
    try:
        pending = write_discover_pending(provider=args.provider)
        result = run_skill_from_pending(pending, provider=args.provider)
        append_log("discover", f"discovery report via {pending.name}")
        mark_stage_done("discovery", output=result.get("output_path"))
        refresh_all()
    except Exception as exc:
        mark_stage_failed("discovery", str(exc))
        raise
    return 0


def cmd_gap(args: argparse.Namespace) -> int:
    provider = provider_for_role("gap", args.provider)
    reject_python_llm_ingest(context="gap", provider=provider)
    mark_stage_in_progress("gap")
    try:
        pending = write_gap_pending(provider=args.provider)
        result = run_skill_from_pending(pending, provider=args.provider)
        append_log("gap", f"gap report via {pending.name}")
        mark_stage_done("gap", output=result.get("output_path"))
        refresh_all()
    except Exception as exc:
        mark_stage_failed("gap", str(exc))
        raise
    return 0


def cmd_evolution(args: argparse.Namespace) -> int:
    provider = provider_for_role("evolution", args.provider)
    reject_python_llm_ingest(context="evolution", provider=provider)
    mark_stage_in_progress("evolution")
    try:
        pending = write_evolution_pending(provider=args.provider)
        result = run_skill_from_pending(pending, provider=args.provider)
        append_log("evolution", f"evolution report via {pending.name}")
        mark_stage_done("evolution", output=result.get("output_path"))
        refresh_all()
    except Exception as exc:
        mark_stage_failed("evolution", str(exc))
        raise
    return 0
