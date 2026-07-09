"""Query pipeline: prepare → run-skill(query) → optional save."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from config import OUTPUTS_DIR, WORKSPACE_PATH
from llm_provider import (
    context_limits,
    model_name,
    provider_for_role,
    provider_name,
)
from pending_cleanup import cleanup_pending_artifacts
from prepare_query import prepare_query
from query_promote import format_promote_suggestion
from query_retrieval import iter_wiki_files, load_index, print_retrieval_debug
from run_skill import run_skill_from_pending

logger = logging.getLogger(__name__)


def sanitize_filename(question: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", question).strip("-")
    safe = re.sub(r"-+", "-", safe)
    return safe[:max_len] or "query"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def save_output(question: str, messages: List[Dict[str, str]]) -> Path:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    last_updated = now.isoformat(timespec="seconds")
    safe_q = sanitize_filename(question)
    out = OUTPUTS_DIR / f"{safe_q}-{date_str}.md"

    dialogue = "\n\n".join(
        [
            f"**{m['role'].capitalize()}**: {m['content']}"
            for m in messages
            if m["role"] != "system"
        ]
    )

    note_content = f"""---
last_updated: {last_updated}
title: {yaml_string(question)}
description: {yaml_string(f"Query-wiki synthesis generated from self-wiki evidence for: {question}")}
level: 1
tags: [type/synthesis, query-wiki]
date: {date_str}
question: {yaml_string(question)}
scope: self-wiki/wiki
---

> This query note captures a reasoning snapshot generated from the curated wiki evidence available at query time. Treat confident claims as valid only when they carry provenance back to the cited wiki or raw sources.
> It is a Level 1 synthesis artifact: useful for reflection and follow-up, but not a replacement for the underlying source notes.

## Query

{question}

## Conversation

{dialogue}

## Evolution

- {date_str}: Created by `query-wiki` from the current `self-wiki/wiki` index and retrieved evidence snippets.

## Backlinks

- **Evolved from**: [[self-wiki/wiki]]
- **Mentioned in**: [[AGENTS.md]]
- **Contradicts**: None identified in this query output.
"""
    out.write_text(note_content, encoding="utf-8")
    return out


def generate_query_answer(
    query: str,
    *,
    index: dict | None = None,
    messages: List[Dict[str, str]] | None = None,
    provider: str | None = None,
    debug_retrieval: bool = False,
) -> dict:
    llm_provider = provider_for_role("query", provider)
    index = index if index is not None else load_index(required=False)
    messages = messages if messages is not None else []

    pending, pending_path = prepare_query(query, index=index, provider=llm_provider)

    if debug_retrieval:
        print_retrieval_debug(
            {
                "profile": pending["profile"],
                "strong_profile": pending["strong_profile"],
                "profile_scores": pending["profile_scores"],
                "query_terms": pending["query_terms"],
                "candidates": pending["candidates"],
            }
        )

    result = run_skill_from_pending(pending_path, provider=llm_provider, write_output=True)
    answer = result["text"]
    cleanup_pending_artifacts(pending_path)

    messages.append({"role": "user", "content": pending["user_message"]})
    messages.append({"role": "assistant", "content": answer})

    return {
        "query": query,
        "answer": answer,
        "provider": llm_provider,
        "model": model_name(llm_provider),
        "profile": pending["profile"],
        "strong_profile": pending["strong_profile"],
        "profile_scores": pending["profile_scores"],
        "language": pending["language"],
        "query_terms": pending["query_terms"],
        "candidates": pending["candidates"],
        "messages": messages,
        "pending_path": str(pending_path.relative_to(pending_path.parent.parent.parent)),
        "answer_path": pending.get("answer_output"),
    }


def run_query(
    query: str,
    *,
    provider: str | None = None,
    debug_retrieval: bool = False,
    save: bool = True,
    promote_suggest: bool | None = None,
) -> dict:
    import os

    if promote_suggest is None:
        promote_suggest = os.environ.get("PROMOTE_SUGGEST", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    result = generate_query_answer(
        query, provider=provider, debug_retrieval=debug_retrieval
    )
    if save:
        out_path = save_output(result["query"], result["messages"])
        result["output_path"] = str(out_path.relative_to(out_path.parent.parent.parent))
        logger.info("Saved query output to %s", out_path)

    if promote_suggest and save:
        suggestion = format_promote_suggestion(
            answer=result["answer"],
            output_path=result.get("output_path"),
            candidates=result.get("candidates"),
            query=result.get("query"),
        )
        if suggestion:
            result["promote_suggestion"] = suggestion
            print(suggestion, file=sys.stderr)
    return result


def print_intro_help() -> None:
    llm_provider = provider_name()
    llm_model = model_name()
    gemini_model = model_name("gemini")
    max_ctx, reserved, max_prompt = context_limits()
    intro = f"""
query-wiki introduction
=======================

Purpose:
- Reason over self-wiki/wiki and answer life queries with provenance.
- Pipeline: prepare-query (deterministic) → run-skill(query.md) → save output.
- Supports Local MLX (OpenAI-compatible) and Google Gemini API.

Current model config:
- LLM_PROVIDER = {llm_provider}
- LLM_MODEL    = {llm_model} (MLX/OpenAI)
- GEMINI_MODEL = {gemini_model}
- MAX_CONTEXT_TOKENS = {max_ctx}
- RESERVED_OUTPUT_TOKENS = {reserved}
- MAX_PROMPT_TOKENS = {max_prompt}

Examples:
- make query Q="what are my values?"
- python scripts/cli.py query "your question"
- python scripts/query_engine.py --list

Tips:
- Run `make sync` to refresh INDEX metadata.
- Use --debug-retrieval to inspect ranking scores.
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


def query_wiki_interactive(
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Query the self-wiki (prepare → run-skill → answer).",
        epilog="Tip: use --intro for full query logic introduction and examples.",
    )
    parser.add_argument("query", nargs="?", help="Your question")
    parser.add_argument("--list", action="store_true", help="List indexed topics and exit.")
    parser.add_argument("--debug-retrieval", action="store_true")
    parser.add_argument("--intro", action="store_true", help="Show introduction/help.")
    parser.add_argument("--save", action="store_true", help="Save answer to self-wiki/outputs.")
    parser.add_argument("--provider", default=None, help="Override LLM_PROVIDER from .env")
    args = parser.parse_args(argv)

    if args.intro:
        print_intro_help()
        return 0

    if not args.query and not args.list:
        print('Usage: python scripts/query_engine.py "Your question" [--debug-retrieval]')
        print("Or:    python scripts/query_engine.py --list")
        print("Or:    make query")
        return 1

    if args.query and args.save:
        result = run_query(args.query, provider=args.provider, debug_retrieval=args.debug_retrieval)
        print(result["answer"])
        print(f"\nSaved to {result.get('output_path', 'self-wiki/outputs/')}")
        return 0

    query_wiki_interactive(
        args.query,
        debug_retrieval=args.debug_retrieval,
        list_mode=args.list,
        provider=args.provider,
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
