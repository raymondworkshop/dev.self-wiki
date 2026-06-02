"""Query pipeline: prepare → run-skill(query) → optional save."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from llm_provider import model_name, normalize_provider
from prepare_query import prepare_query
from query_retrieval import load_index, print_retrieval_debug
from run_skill import run_skill_from_pending
from save_query_output import save_output

logger = logging.getLogger(__name__)


def generate_query_answer(
    query: str,
    *,
    index: dict | None = None,
    messages: List[Dict[str, str]] | None = None,
    provider: str | None = None,
    debug_retrieval: bool = False,
) -> dict:
    llm_provider = normalize_provider(provider)
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
) -> dict:
    result = generate_query_answer(
        query, provider=provider, debug_retrieval=debug_retrieval
    )
    if save:
        out_path = save_output(result["query"], result["messages"])
        result["output_path"] = str(out_path.relative_to(out_path.parent.parent.parent))
        logger.info("Saved query output to %s", out_path)
    return result
