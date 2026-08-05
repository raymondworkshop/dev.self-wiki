"""rdatabase CLI command handlers."""

from __future__ import annotations

import argparse
import logging

from config import WORKSPACE_PATH, workspace_relpath
from llm_provider import model_name, provider_for_role
from log_utils import append_log
from prepare_rdatabase import prepare_rdatabase
from rdatabase_engine import run_rdatabase
from rdatabase_index import build_index

logger = logging.getLogger(__name__)


def cmd_rdatabase_index(args: argparse.Namespace) -> int:
    idx = build_index(force=args.force)
    print(
        f"rdatabase-index: {idx['file_count']} files, {idx['paragraph_count']} paragraphs "
        f"(digest={idx.get('digest')})"
    )
    verb = "rebuilt" if args.force else "updated"
    append_log(
        "rdatabase-index",
        f"{verb} log/rdatabase-index.json | files={idx['file_count']} paragraphs={idx['paragraph_count']}",
    )
    return 0


def cmd_prepare_rdatabase(args: argparse.Namespace) -> int:
    pending, path = prepare_rdatabase(args.query, provider=args.provider)
    logger.info("Prepared rdatabase pending: %s", workspace_relpath(path))
    logger.info(
        "language=%s candidates=%s terms=%s",
        pending["language"],
        len(pending.get("candidates") or []),
        len(pending.get("query_terms") or []),
    )
    return 0


def cmd_rdatabase(args: argparse.Namespace) -> int:
    llm_provider = provider_for_role("rdatabase", args.provider)
    logger.info(
        "rdatabase LLM: provider=%s model=%s",
        llm_provider,
        model_name(llm_provider, role="rdatabase"),
    )
    result = run_rdatabase(
        args.query,
        provider=args.provider,
        debug_retrieval=args.debug_retrieval,
        save=not args.no_save,
        force_index=args.force_index,
    )
    print(result["answer"])
    if result.get("output_path"):
        logger.info("Saved to %s", result["output_path"])
    return 0
