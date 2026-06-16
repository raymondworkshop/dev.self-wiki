#!/usr/bin/env python3
"""Thin CLI harness: prepare → run-skill → apply → post (MVP ingest)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from cli_cmd_analysis import cmd_discover, cmd_evolution, cmd_gap
from cli_cmd_basic import cmd_apply_ingest, cmd_post_ingest, cmd_run_skill
from cli_cmd_pipeline import (
    cmd_apply_compression,
    cmd_compress,
    cmd_progress,
    cmd_register_reference,
    cmd_sync,
    cmd_wiki_synthesize,
)
from cli_cmd_query import (
    cmd_doctor_config,
    cmd_lint,
    cmd_prepare_lint,
    cmd_prepare_query,
    cmd_promote,
    cmd_query,
    cmd_twin,
)
from cli_shared import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Self-Wiki thin harness")
    sub = parser.add_subparsers(dest="command")

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

    p_apply = sub.add_parser(
        "apply-ingest",
        help="Apply wiki-synthesize actions JSON to wiki pages",
    )
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
    p_progress.add_argument("--wiki-synth-only", action="store_true", help="Wiki-synthesize manifest only")
    p_progress.set_defaults(func=cmd_progress)

    p_ws = sub.add_parser(
        "wiki-synthesize",
        help="Link compression/ digests into wiki/ via wiki-synthesize skill",
    )
    p_ws.add_argument("--file", help="Single compression rel path e.g. compression/origin-apple-notes/foo.md")
    p_ws.add_argument("--provider", default=None)
    p_ws.add_argument("--limit", type=int, default=None, help="Max files per run")
    p_ws.add_argument("--force", action="store_true", help="Re-run even if manifest marks done")
    p_ws.add_argument("--folder", default=None, help="Only under compression/<folder>/")
    p_ws.add_argument(
        "--wave",
        default=None,
        choices=["theme_links"],
        help="Filter wave: theme_links = only digests with ## Theme links",
    )
    p_ws.add_argument("--post-ingest", action="store_true", help="Run post-ingest after batch")
    p_ws.set_defaults(func=cmd_wiki_synthesize)

    p_discover = sub.add_parser("discover", help="Unknown-known pattern report → discovery/")
    p_discover.add_argument("--provider", default=None)
    p_discover.set_defaults(func=cmd_discover)

    p_gap = sub.add_parser("gap", help="Knowledge gap report → gap/")
    p_gap.add_argument("--provider", default=None)
    p_gap.set_defaults(func=cmd_gap)

    p_evolution = sub.add_parser("evolution", help="Knowledge evolution report → evolution/")
    p_evolution.add_argument("--provider", default=None)
    p_evolution.set_defaults(func=cmd_evolution)

    p_apply_comp = sub.add_parser("apply-compression", help="Apply compression JSON or batch digests")
    p_apply_comp.add_argument("--file", required=True, help="Path to compression actions JSON")
    p_apply_comp.set_defaults(func=cmd_apply_compression)

    p_sync = sub.add_parser("sync", help="Changed raw → compression/ (profile-routed)")
    p_sync.add_argument("--provider", default=None)
    p_sync.add_argument("--file", help="Single raw rel path under self-wiki/raw/")
    p_sync.set_defaults(func=cmd_sync)

    p_doctor = sub.add_parser(
        "doctor-config",
        help="Print resolved provider/model/skill for core stages",
    )
    p_doctor.add_argument(
        "--raw",
        default="raw/_posts/example.md",
        help="Sample raw path used to resolve profile-routed skills",
    )
    p_doctor.add_argument("--provider", default=None, help="Global override provider")
    p_doctor.add_argument("--compress-provider", default=None, help="Override compress provider")
    p_doctor.add_argument("--wiki-provider", default=None, help="Override wiki-synthesize provider")
    p_doctor.add_argument("--query-provider", default=None, help="Override query provider")
    p_doctor.add_argument("--lint-provider", default=None, help="Override lint provider")
    p_doctor.set_defaults(func=cmd_doctor_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
