"""Query/lint/twin/promote/doctor CLI command handlers."""

from __future__ import annotations

import argparse
import logging

from build_twin_profile import build_twin_profile
from config import WORKSPACE_PATH
from ingest_profiles import resolve_profile
from llm_provider import model_name, provider_for_role
from log_utils import append_log
from pending_cleanup import cleanup_pending_artifacts
from prepare_lint import merge_lint_into_audit, write_pending as write_lint_pending
from prepare_query import prepare_query
from promote_output import promote_output
from query_engine import run_query
from run_skill import run_skill_from_pending
from skill_registry import resolve_skill

logger = logging.getLogger(__name__)


def cmd_prepare_query(args: argparse.Namespace) -> int:
    pending, path = prepare_query(args.query, provider=args.provider)
    logger.info("Prepared query pending: %s", path.relative_to(WORKSPACE_PATH))
    logger.info("Profile: %s (strong=%s)", pending["profile"], pending["strong_profile"])
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    import os

    llm_provider = provider_for_role("query", args.provider)
    logger.info("Query LLM: provider=%s model=%s", llm_provider, model_name(llm_provider))
    promote_suggest = None
    if getattr(args, "no_promote_suggest", False):
        promote_suggest = False
    elif os.environ.get("PROMOTE_SUGGEST", "").strip().lower() in ("0", "false", "no"):
        promote_suggest = False
    result = run_query(
        args.query,
        provider=args.provider,
        debug_retrieval=args.debug_retrieval,
        save=not args.no_save,
        promote_suggest=promote_suggest,
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
    cleanup_pending_artifacts(pending_path)
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
        logger.info(
            "Dry run: would promote %s → %s (%d bytes)",
            result["output"],
            result["target"],
            result["bytes"],
        )
        if result.get("preview"):
            print(result["preview"])
    return 0


def cmd_doctor_config(args: argparse.Namespace) -> int:
    raw_rel = (args.raw or "raw/_posts/example.md").replace("\\", "/")
    if not raw_rel.startswith("raw/"):
        raw_rel = f"raw/{raw_rel}"

    profile = resolve_profile(raw_rel) or {}
    profile_wiki_skill = profile.get("wiki_skill", "skills/wiki-synthesize.md")

    wiki_provider = provider_for_role("wiki_synthesize", args.wiki_provider or args.provider)
    query_provider = provider_for_role("query", args.query_provider or args.provider)
    lint_provider = provider_for_role("lint", args.lint_provider or args.provider)

    wiki_skill = resolve_skill(
        "wiki_synthesize",
        profile_wiki_skill,
        raw_rel=raw_rel,
        current_skill=profile.get("wiki_skill"),
    )
    query_skill = resolve_skill("query", "skills/query.md")
    lint_skill = resolve_skill("lint", "skills/lint.md")

    print(f"raw_path: {raw_rel}")
    print(f"profile: {profile.get('name', '(no matched profile)')}")
    print("")
    print("[raw -> wiki]")
    print(f"provider={wiki_provider}")
    print(f"model={model_name(wiki_provider)}")
    print(f"skill={wiki_skill}")
    print("")
    print("[query]")
    print(f"provider={query_provider}")
    print(f"model={model_name(query_provider)}")
    print(f"skill={query_skill}")
    print("")
    print("[lint]")
    print(f"provider={lint_provider}")
    print(f"model={model_name(lint_provider)}")
    print(f"skill={lint_skill}")
    return 0
