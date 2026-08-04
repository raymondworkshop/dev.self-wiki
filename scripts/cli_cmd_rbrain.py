"""rbrain CLI command handlers."""

from __future__ import annotations

import argparse
import logging

from config import WORKSPACE_PATH, workspace_relpath
from llm_provider import model_name, provider_for_role
from log_utils import append_log
from prepare_rbrain import prepare_rbrain
from rbrain_engine import run_rbrain
from rbrain_index import build_index

logger = logging.getLogger(__name__)


def cmd_rbrain_index(args: argparse.Namespace) -> int:
    idx = build_index(force=args.force)
    print(
        f"rbrain-index: {idx['file_count']} files, {idx['paragraph_count']} paragraphs "
        f"(digest={idx.get('digest')})"
    )
    verb = "rebuilt" if args.force else "updated"
    append_log(
        "rbrain-index",
        f"{verb} log/rbrain-index.json | files={idx['file_count']} paragraphs={idx['paragraph_count']}",
    )
    return 0


def cmd_prepare_rbrain(args: argparse.Namespace) -> int:
    pending, path = prepare_rbrain(args.query, provider=args.provider)
    logger.info("Prepared rbrain pending: %s", workspace_relpath(path))
    logger.info(
        "language=%s candidates=%s terms=%s",
        pending["language"],
        len(pending.get("candidates") or []),
        len(pending.get("query_terms") or []),
    )
    return 0


def cmd_rbrain(args: argparse.Namespace) -> int:
    llm_provider = provider_for_role("rbrain", args.provider)
    logger.info(
        "rbrain LLM: provider=%s model=%s",
        llm_provider,
        model_name(llm_provider, role="rbrain"),
    )
    result = run_rbrain(
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
