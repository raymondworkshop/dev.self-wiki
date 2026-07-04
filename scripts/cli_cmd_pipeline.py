"""Pipeline-oriented CLI command handlers."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from apply_compression import apply_batch_digests, apply_from_file as apply_compression_from_file
from composer_policy import reject_python_llm_ingest
from compression_manifest import print_status as print_compression_status
from compress_raw import compress_all, compress_file, sync_changed_files
from config import RAW_DIR, WORKSPACE_PATH
from llm_provider import provider_for_role
from pipeline_progress import mark_stage_done, print_status as print_pipeline_status, refresh_all
from register_reference import register_references
from wiki_synth_manifest import print_status as print_wiki_synth_status
from wiki_synthesize import synthesize_all, synthesize_compression_file
from cli_shared import post_ingest

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


def cmd_wiki_synthesize(args: argparse.Namespace) -> int:
    provider = provider_for_role("wiki_synthesize", args.provider)
    reject_python_llm_ingest(context="wiki-synthesize", provider=provider)
    if args.file:
        comp = Path(args.file)
        if not comp.is_absolute():
            comp = WORKSPACE_PATH / comp
        if not comp.is_file():
            logger.error("Compression file not found: %s", args.file)
            return 1
        pages = synthesize_compression_file(comp, provider=provider)
        logger.info("Applied %d wiki page update(s)", pages)
        if args.post_ingest:
            post_ingest(f"wiki-synthesize 1 file, {pages} page(s)")
        return 0

    processed = synthesize_all(
        provider=provider,
        limit=args.limit,
        force=args.force,
        folder=args.folder,
        wave=args.wave,
    )
    if processed and args.post_ingest:
        post_ingest(f"wiki-synthesize {len(processed)} compression file(s)")
    elif processed:
        logger.info(
            "Done: wiki-synthesize %d file(s) (run post-ingest to refresh index/twin)",
            len(processed),
        )
    else:
        logger.info("No compression files wiki-synthesized.")
    return 0


def cmd_compress(args: argparse.Namespace) -> int:
    provider = provider_for_role("compress", args.provider)
    reject_python_llm_ingest(context="compress", provider=provider)
    if args.file:
        rel = args.file
        if rel.startswith("raw/"):
            rel = rel[len("raw/") :]
        abs_p = RAW_DIR / rel
        if not abs_p.exists():
            logger.error("Raw file not found: %s", rel)
            return 1
        out = compress_file(rel, abs_p, provider=provider)
        if out:
            logger.info("Wrote %s", out.relative_to(WORKSPACE_PATH))
        return 0

    compressed = compress_all(
        provider=provider,
        limit=args.limit,
        force=args.force,
        folder=args.folder,
    )
    refresh_all()
    if compressed:
        summary = f"compressed {len(compressed)} raw file(s)"
        if args.post_ingest:
            post_ingest(summary)
        else:
            logger.info("Done: %s (run post-ingest to refresh index/twin)", summary)
    else:
        logger.info("No files compressed.")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    if args.wiki_synth_only:
        print_wiki_synth_status(folder=args.folder)
    elif args.compression_only:
        print_compression_status(folder=args.folder)
    else:
        print_pipeline_status()
    return 0


def cmd_apply_compression(args: argparse.Namespace) -> int:
    actions = Path(args.file)
    if not actions.is_absolute():
        actions = WORKSPACE_PATH / actions
    data = json.loads(actions.read_text(encoding="utf-8"))
    if "digests" in data:
        paths = apply_batch_digests(data)
        logger.info("Applied %d compression file(s)", len(paths))
    else:
        path = apply_compression_from_file(actions)
        logger.info("Wrote %s", path.relative_to(WORKSPACE_PATH))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    provider = provider_for_role("compress", args.provider)
    reject_python_llm_ingest(context="sync", provider=provider)
    compressed = sync_changed_files(provider=provider, file_filter=args.file)
    if compressed:
        if os.environ.get("SYNC_SKIP_POST_INGEST", "0").strip().lower() in ("1", "true", "yes"):
            logger.info(
                "Sync complete: %d raw file(s) compressed (post-ingest skipped)",
                len(compressed),
            )
        else:
            post_ingest(f"sync compressed {len(compressed)} raw file(s)")
    else:
        logger.info("Nothing synced.")
    return 0
