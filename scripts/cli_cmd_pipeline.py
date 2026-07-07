"""Pipeline-oriented CLI command handlers."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from composer_policy import reject_python_llm_ingest
from config import WORKSPACE_PATH
from llm_provider import provider_for_role
from pipeline_progress import mark_stage_done, print_status as print_pipeline_status
from register_reference import register_references
from wiki_synth_manifest import print_status as print_wiki_synth_status
from wiki_synthesize import synthesize_all, synthesize_raw_file, sync_changed_raw_files
from cli_shared import ingest

logger = logging.getLogger(__name__)


def cmd_register_reference(args: argparse.Namespace) -> int:
    path = register_references(dry_run=args.dry_run)
    if not args.dry_run:
        catalog = json.loads(path.read_text(encoding="utf-8"))
        logger.info(
            "Registered %d twitter entries → %s",
            catalog["count"],
            path.relative_to(WORKSPACE_PATH),
        )
        mark_stage_done(
            "register_reference",
            output=str(path.relative_to(WORKSPACE_PATH)),
            detail={"count": catalog["count"]},
        )
    return 0


def _run_ingest(summary: str, args: argparse.Namespace) -> None:
    if getattr(args, "ingest", False):
        ingest(summary)


def cmd_wiki_synthesize(args: argparse.Namespace) -> int:
    provider = provider_for_role("wiki_synthesize", args.provider)
    reject_python_llm_ingest(context="wiki-synthesize", provider=provider)
    if args.file:
        raw = Path(args.file)
        if not raw.is_absolute():
            raw = WORKSPACE_PATH / raw
        if not raw.is_file():
            logger.error("Raw file not found: %s", args.file)
            return 1
        pages = synthesize_raw_file(raw, provider=provider)
        logger.info("Applied %d wiki page update(s)", pages)
        _run_ingest(f"wiki-synthesize 1 file, {pages} page(s)", args)
        return 0

    processed = synthesize_all(
        provider=provider,
        limit=args.limit,
        force=args.force,
        folder=args.folder,
        wave=args.wave,
    )
    if processed:
        _run_ingest(f"wiki-synthesize {len(processed)} raw file(s)", args)
    else:
        logger.info("No raw files wiki-synthesized.")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    if args.wiki_synth_only:
        print_wiki_synth_status(folder=args.folder)
    else:
        print_pipeline_status()
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    provider = provider_for_role("wiki_synthesize", args.provider)
    reject_python_llm_ingest(context="sync", provider=provider)
    processed = sync_changed_raw_files(provider=provider, file_filter=args.file)
    if processed:
        logger.info("Sync complete: %d raw file(s) wiki-synthesized", len(processed))
    else:
        logger.info("Nothing to sync (no changed raw files).")
    return 0
