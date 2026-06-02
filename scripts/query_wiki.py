#!/usr/bin/env python3
"""Thin CLI wrapper for query-wiki (prepare → run-skill → save)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config import WORKSPACE_PATH
from llm_provider import (
    context_limits,
    model_name,
    provider_name,
)
from query_engine import generate_query_answer, run_query
from query_retrieval import iter_wiki_files, load_index, print_retrieval_debug
from save_query_output import save_output

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WIKI_ROOT = WORKSPACE_PATH / "self-wiki" / "wiki"
OUTPUT_ROOT = WORKSPACE_PATH / "self-wiki" / "outputs"
INDEX_PATH = WORKSPACE_PATH / "self-wiki" / "log" / "INDEX.json"

LLM_PROVIDER = provider_name()
LLM_MODEL = model_name()
GEMINI_MODEL = model_name("gemini")
MAX_CONTEXT_TOKENS, RESERVED_OUTPUT_TOKENS, MAX_PROMPT_TOKENS = context_limits()


def print_intro_help() -> None:
    intro = f"""
query-wiki introduction
=======================

Purpose:
- Reason over self-wiki/wiki and answer life queries with provenance.
- Pipeline: prepare-query (deterministic) → run-skill(query.md) → save output.
- Supports Local MLX (OpenAI-compatible) and Google Gemini API.

Current model config:
- LLM_PROVIDER = {LLM_PROVIDER}
- LLM_MODEL    = {LLM_MODEL} (MLX/OpenAI)
- GEMINI_MODEL = {GEMINI_MODEL}
- MAX_CONTEXT_TOKENS = {MAX_CONTEXT_TOKENS}
- RESERVED_OUTPUT_TOKENS = {RESERVED_OUTPUT_TOKENS}
- MAX_PROMPT_TOKENS = {MAX_PROMPT_TOKENS}

Built-in query logic:
1) Detect question profile (values / personality_logic / swot / general)
2) Score profile confidence (strong only if best>=6 and best-second>=2)
3) Build bilingual retrieval keywords (deterministic only — no LLM expand)
4) Rank full-text wiki matches plus INDEX metadata when available
5) Select high-signal candidates and extract evidence snippets
6) One LLM call via skills/query.md for synthesis with provenance

Examples:
- python3 scripts/query_wiki.py "what are my values?"
- python3 scripts/query_wiki.py "請分析我的性格和底層邏輯"
- python3 scripts/query_wiki.py "分析我的優點，弱點，盲點" --debug-retrieval
- python3 scripts/query_wiki.py --list
- make query

Tips:
- Run `make sync` to refresh INDEX metadata; query falls back to full-text scan if INDEX is missing.
- Use --debug-retrieval to inspect ranking scores and matched terms.
"""
    print(intro.strip())


def perform_query_turn(
    query: str,
    index: dict,
    messages: list,
    debug_retrieval: bool,
    *,
    provider: str | None = None,
) -> None:
    try:
        result = generate_query_answer(
            query,
            index=index,
            messages=messages,
            provider=provider,
            debug_retrieval=debug_retrieval,
        )
    except RuntimeError:
        logger.error("Failed to generate answer from LLM.")
        return

    print(f"\n--- ANSWER ---\n{result['answer']}")


def query_wiki(
    query: str | None,
    debug_retrieval: bool = False,
    list_mode: bool = False,
    *,
    provider: str | None = None,
) -> None:
    if list_mode:
        index = load_index(required=False)
        print("Available topics:")
        topics = sorted(index.get("topics", {}).keys())
        if topics:
            print("\n".join(topics))
        else:
            print("\n".join(str(p.relative_to(WORKSPACE_PATH)) for p in iter_wiki_files()))
        return

    index = load_index(required=False)
    messages: list = []
    first_query = query

    if query:
        perform_query_turn(query, index, messages, debug_retrieval, provider=provider)

    print("Starting interactive session. Type 'quit' or 'exit' to finish.")
    while True:
        q = input("\nQuery: ").strip()
        if q.lower() in ["quit", "exit"]:
            break
        if not q:
            continue
        if not first_query:
            first_query = q
        perform_query_turn(q, index, messages, debug_retrieval, provider=provider)

    if messages and first_query:
        save_choice = input("\nSave this conversation? [y/N]: ").strip().lower()
        if save_choice == "y":
            out_path = save_output(first_query, messages)
            print(f"Conversation saved to {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query the self-wiki (prepare → run-skill → answer).",
        epilog="Tip: use --intro for full query logic introduction and examples.",
    )
    parser.add_argument("query", nargs="?", help="Your question")
    parser.add_argument("--list", action="store_true", help="List indexed topics and exit.")
    parser.add_argument(
        "--debug-retrieval",
        action="store_true",
        help="Print retrieval ranking scores and selected candidates.",
    )
    parser.add_argument("--intro", action="store_true", help="Show introduction/help.")
    parser.add_argument("--save", action="store_true", help="Save answer to self-wiki/outputs.")
    parser.add_argument("--provider", default=None, help="Override LLM_PROVIDER from .env")

    args = parser.parse_args()

    if args.intro:
        print_intro_help()
        return 0

    if not args.query and not args.list:
        print('Usage: python3 scripts/query_wiki.py "Your question" [--debug-retrieval]')
        print("Or:    python3 scripts/query_wiki.py --list")
        print("Use --intro for full introduction/help.")
        return 1

    if args.query and args.save:
        result = run_query(args.query, provider=args.provider, debug_retrieval=args.debug_retrieval)
        print(result["answer"])
        print(f"\nSaved to {result.get('output_path', 'self-wiki/outputs/')}")
        return 0

    query_wiki(
        args.query,
        debug_retrieval=args.debug_retrieval,
        list_mode=args.list,
        provider=args.provider,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
