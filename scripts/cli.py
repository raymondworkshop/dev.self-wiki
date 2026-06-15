#!/usr/bin/env python3
"""Thin CLI harness: prepare → run-skill → apply → post (MVP ingest)."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from apply_ingest import apply_from_file
from apply_compression import apply_from_file as apply_compression_from_file  # noqa: F401
from build_twin_profile import build_twin_profile
from compress_raw import compress_file, compress_all
from config import LOG_DIR, RAW_DIR, WORKSPACE_PATH
from llm_provider import (
    fallback_provider_chain,
    model_name,
    normalize_provider,
    provider_for_role,
)
from log_utils import append_log
from orchestrator import SocraticOrchestrator
from pending_cleanup import cleanup_pending_pair, json_actions_path, prune_old_pending
from prepare_discover import write_pending as write_discover_pending
from prepare_evolution import write_pending as write_evolution_pending
from prepare_gap import write_pending as write_gap_pending
from prepare_ingest import prepare_for_file
from prepare_lint import merge_lint_into_audit, write_pending as write_lint_pending
from prepare_query import prepare_query
from promote_output import promote_output
from query_engine import run_query
from composer_policy import reject_python_llm_ingest
from compression_manifest import print_status as print_compression_status
from pipeline_progress import (
    mark_stage_done,
    mark_stage_failed,
    mark_stage_in_progress,
    print_status as print_pipeline_status,
    refresh_all,
)
from refresh_index import refresh_index
from register_reference import register_references
from run_skill import run_skill_from_pending

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "sync_v2.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _python() -> str:
    return sys.executable


def post_ingest(summary: str = "post-ingest complete") -> None:
    scripts = Path(__file__).parent
    subprocess.run([_python(), str(scripts / "backliner.py")], check=True)
    refresh_index()
    build_twin_profile()
    append_log("ingest", summary)
    mark_stage_done("post_ingest")
    retain_days = int(os.environ.get("PENDING_RETAIN_DAYS", "7"))
    if retain_days >= 0:
        pruned = prune_old_pending(retain_days, keep_failed=True, dry_run=False)
        if pruned:
            logger.info("Pruned %d stale pending file(s) older than %d days", len(pruned), retain_days)


def cmd_prepare_ingest(args: argparse.Namespace) -> int:
    orchestrator = SocraticOrchestrator()
    changed = orchestrator.get_changed_files()
    if not changed:
        logger.info("No changed raw files.")
        return 0

    for rel, abs_p, file_hash in changed:
        if args.file and rel != args.file:
            continue
        paths = prepare_for_file(rel, abs_p, file_hash)
        for p in paths:
            logger.info("Prepared %s", p.relative_to(WORKSPACE_PATH))
    return 0


def cmd_run_skill(args: argparse.Namespace) -> int:
    pending = Path(args.pending)
    if not pending.is_absolute():
        pending = WORKSPACE_PATH / pending
    run_skill_from_pending(pending, provider=args.provider)
    if args.apply:
        actions_path = json_actions_path(pending)
        count = apply_from_file(actions_path, rel_path=args.raw)
        logger.info("Applied %d page update(s)", count)
        if count >= 0 and os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
            cleanup_pending_pair(pending)
    return 0


def cmd_apply_ingest(args: argparse.Namespace) -> int:
    actions = Path(args.file)
    if not actions.is_absolute():
        actions = WORKSPACE_PATH / actions
    count = apply_from_file(actions, rel_path=args.raw)
    logger.info("Applied %d page update(s)", count)
    if count >= 0 and args.pending:
        pending = Path(args.pending)
        if not pending.is_absolute():
            pending = WORKSPACE_PATH / pending
        if os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
            cleanup_pending_pair(pending)
    return 0


def cmd_post_ingest(args: argparse.Namespace) -> int:
    post_ingest(args.summary)
    return 0


def cmd_register_reference(args: argparse.Namespace) -> int:
    path = register_references(dry_run=args.dry_run)
    if not args.dry_run:
        import json

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


def cmd_compress(args: argparse.Namespace) -> int:
    provider = provider_for_role("sync", args.provider)
    reject_python_llm_ingest(context="compress", provider=provider)
    if args.file:
        rel = args.file
        if rel.startswith("raw/"):
            rel = rel[len("raw/") :]
        abs_p = RAW_DIR / rel
        if not abs_p.exists():
            logger.error("Raw file not found: %s", rel)
            return 1
        out = compress_file(rel, abs_p, provider=args.provider)
        if out:
            logger.info("Wrote %s", out.relative_to(WORKSPACE_PATH))
        return 0

    compressed = compress_all(
        provider=args.provider,
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


def cmd_prepare_query(args: argparse.Namespace) -> int:
    pending, path = prepare_query(args.query, provider=args.provider)
    logger.info("Prepared query pending: %s", path.relative_to(WORKSPACE_PATH))
    logger.info("Profile: %s (strong=%s)", pending["profile"], pending["strong_profile"])
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    llm_provider = provider_for_role("query", args.provider)
    logger.info("Query LLM: provider=%s model=%s", llm_provider, model_name(llm_provider))
    result = run_query(
        args.query,
        provider=args.provider,
        debug_retrieval=args.debug_retrieval,
        save=not args.no_save,
    )
    print(result["answer"])
    if result.get("output_path"):
        logger.info("Saved to %s", result["output_path"])
    return 0


def cmd_prepare_lint(args: argparse.Namespace) -> int:
    path = write_lint_pending()
    logger.info("Prepared lint pending: %s", path.relative_to(WORKSPACE_PATH))
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    llm_provider = provider_for_role("lint", args.provider)
    logger.info("Lint LLM: provider=%s model=%s", llm_provider, model_name(llm_provider))
    pending_path = write_lint_pending()
    result = run_skill_from_pending(pending_path, provider=llm_provider)
    merge_lint_into_audit(result["text"])
    append_log("lint", "Global cognitive lint merged into audit.md")
    logger.info("Lint complete; audit.md updated")
    return 0


def cmd_twin(args: argparse.Namespace) -> int:
    path = build_twin_profile()
    logger.info("Twin profile: %s", path.relative_to(WORKSPACE_PATH))
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    result = promote_output(
        args.file,
        args.target,
        confirm=args.confirm,
    )
    if result.get("applied"):
        logger.info("Promoted to %s", result["target"])
    else:
        logger.info("Dry run: would promote %s → %s (%d bytes)", result["output"], result["target"], result["bytes"])
        if result.get("preview"):
            print(result["preview"])
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    if args.compression_only:
        print_compression_status(folder=args.folder)
    else:
        print_pipeline_status()
    return 0


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


def cmd_sync(args: argparse.Namespace) -> int:
    import sys

    print(
        "Warning: legacy sync writes wiki/ via ingest.md. "
        "Prefer: cli.py compress → post-ingest",
        file=sys.stderr,
    )
    orchestrator = SocraticOrchestrator()
    changed = orchestrator.get_changed_files()
    if args.file:
        changed = [item for item in changed if item[0] == args.file]
        if not changed:
            logger.info("No changed raw file matched --file=%s", args.file)
            return 0
    if not changed:
        logger.info("Nothing to sync.")
        return 0

    primary = normalize_provider(args.provider)
    logger.info("Sync LLM: provider=%s model=%s", primary, model_name(primary))
    providers = fallback_provider_chain(args.provider, role="sync")
    if len(providers) > 1:
        logger.info("Sync fallback chain: %s", " → ".join(providers))

    ingested: list[str] = []
    total_pages = 0

    for rel, abs_p, file_hash in changed:
        logger.info("Syncing raw file: %s", rel)
        pending_paths = prepare_for_file(rel, abs_p, file_hash)
        file_ok = True

        for pending_path in pending_paths:
            try:
                data = run_skill_from_pending(
                    pending_path, provider=args.provider, write_actions=True
                )
                actions_path = json_actions_path(pending_path)
                pages = apply_from_file(actions_path, rel_path=rel)
                total_pages += pages
                if pages == 0 and not data.get("actions"):
                    logger.warning("No actions applied for %s", pending_path.name)
                elif os.environ.get("PENDING_RETAIN_ON_SUCCESS", "0") != "1":
                    cleanup_pending_pair(pending_path)
            except Exception as exc:
                logger.error("Failed ingest for %s: %s", rel, exc)
                file_ok = False
                break

        if file_ok:
            orchestrator.cache[rel] = hashlib.md5(abs_p.read_bytes()).hexdigest()
            orchestrator.save_cache()
            ingested.append(rel)
        else:
            logger.warning("Skipping cache update for %s due to failure.", rel)

    if ingested:
        summary = f"{len(ingested)} raw file(s), {total_pages} page update(s)"
        post_ingest(summary)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Self-Wiki thin harness")
    sub = parser.add_subparsers(dest="command")

    p_prepare = sub.add_parser("prepare-ingest", help="Build pending JSON for changed raw")
    p_prepare.add_argument("--file", help="Single raw rel path under self-wiki/raw/")
    p_prepare.set_defaults(func=cmd_prepare_ingest)

    p_pquery = sub.add_parser("prepare-query", help="Build pending JSON for a query (no LLM)")
    p_pquery.add_argument("query", help="Question text")
    p_pquery.add_argument("--provider", default=None)
    p_pquery.set_defaults(func=cmd_prepare_query)

    p_query = sub.add_parser("query", help="Full query pipeline (prepare → run-skill → save)")
    p_query.add_argument("query", help="Question text")
    p_query.add_argument("--provider", default=None)
    p_query.add_argument("--debug-retrieval", action="store_true")
    p_query.add_argument("--no-save", action="store_true")
    p_query.set_defaults(func=cmd_query)

    p_plint = sub.add_parser("prepare-lint", help="Build pending JSON for global cognitive lint")
    p_plint.set_defaults(func=cmd_prepare_lint)

    p_lint = sub.add_parser("lint", help="Global cognitive lint → merge into audit.md")
    p_lint.add_argument("--provider", default=None)
    p_lint.set_defaults(func=cmd_lint)

    p_twin = sub.add_parser("twin", help="Rebuild twin/PROFILE.md from wiki (deterministic)")
    p_twin.set_defaults(func=cmd_twin)

    p_promote = sub.add_parser("promote", help="Promote query output into wiki page (dry-run unless --confirm)")
    p_promote.add_argument("--file", required=True, help="Path to self-wiki/outputs/….md")
    p_promote.add_argument("--target", required=True, help="Exact wiki page title")
    p_promote.add_argument("--confirm", action="store_true", help="Apply merge (default: dry-run)")
    p_promote.set_defaults(func=cmd_promote)

    p_run = sub.add_parser("run-skill", help="Execute skill for one pending package")
    p_run.add_argument("pending", help="Path to pending JSON")
    p_run.add_argument("--provider", default=None)
    p_run.add_argument("--apply", action="store_true", help="Apply actions and cleanup pair")
    p_run.add_argument("--raw", default=None, help="Raw rel path when using --apply")
    p_run.set_defaults(func=cmd_run_skill)

    p_apply = sub.add_parser("apply-ingest", help="Apply actions JSON to wiki")
    p_apply.add_argument("--file", required=True, help="Path to actions JSON")
    p_apply.add_argument("--raw", default=None, help="Raw rel path for provenance")
    p_apply.add_argument("--pending", default=None, help="Pending JSON path for cleanup after apply")
    p_apply.set_defaults(func=cmd_apply_ingest)

    p_post = sub.add_parser("post-ingest", help="Run backliner, refresh index, twin, append log")
    p_post.add_argument("--summary", default="post-ingest complete")
    p_post.set_defaults(func=cmd_post_ingest)

    p_reg = sub.add_parser("register-reference", help="Catalog twitter raw → log/sources.json (no LLM)")
    p_reg.add_argument("--dry-run", action="store_true")
    p_reg.set_defaults(func=cmd_register_reference)

    p_compress = sub.add_parser("compress", help="Compress raw → compression/ via ingest skills")
    p_compress.add_argument("--file", help="Single raw rel path under self-wiki/raw/")
    p_compress.add_argument("--provider", default=None)
    p_compress.add_argument("--limit", type=int, default=None, help="Max files per run")
    p_compress.add_argument("--force", action="store_true", help="Recompress even if up to date")
    p_compress.add_argument("--folder", default=None, help="Only under raw/<folder>/ e.g. origin-apple-notes")
    p_compress.add_argument("--post-ingest", action="store_true", help="Run post-ingest after batch")
    p_compress.set_defaults(func=cmd_compress)

    p_progress = sub.add_parser("progress", help="Show pipeline progress + resume hints")
    p_progress.add_argument("--compression-only", action="store_true", help="Compression file checklist only")
    p_progress.add_argument("--folder", default=None, help="Filter compression status by folder")
    p_progress.set_defaults(func=cmd_progress)

    p_discover = sub.add_parser("discover", help="Unknown-known pattern report → discovery/")
    p_discover.add_argument("--provider", default=None)
    p_discover.set_defaults(func=cmd_discover)

    p_gap = sub.add_parser("gap", help="Knowledge gap report → gap/")
    p_gap.add_argument("--provider", default=None)
    p_gap.set_defaults(func=cmd_gap)

    p_evolution = sub.add_parser("evolution", help="Knowledge evolution report → evolution/")
    p_evolution.add_argument("--provider", default=None)
    p_evolution.set_defaults(func=cmd_evolution)

    p_sync = sub.add_parser("sync", help="Full ingest pipeline")
    p_sync.add_argument("--provider", default=None)
    p_sync.add_argument("--file", help="Single raw rel path under self-wiki/raw/")
    p_sync.set_defaults(func=cmd_sync)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
