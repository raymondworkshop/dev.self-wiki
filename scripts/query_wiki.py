import json
import logging
import os
import re
import sys
from pathlib import Path

import requests

# Simple vector search implementation using word overlap as a proxy for RAG
# (Avoiding heavy vector DB dependencies for local simplicity)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def expand_query_terms(query):
    # Use LLM to get keywords in both Chinese and English
    llm_provider = os.environ.get("LLM_PROVIDER", "mlx").lower()
    llm_model = os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit")

    prompt = f"""
    Given the following user query, provide a list of search keywords in both Chinese and English, separated by spaces.
    Only output the keywords, nothing else.

    USER QUERY: {query}
    KEYWORDS:
    """

    url = os.environ.get("LLM_URL", "http://100.90.225.26:8080/v1/chat/completions")
    payload = {
        "model": llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        result = (
            response.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        return set(result.lower().split())
    except Exception:
        # Fallback to simple split if LLM fails
        return set(query.lower().split())


def query_wiki(query):
    # ... (Env loading logic)
    workspace = Path(
        os.environ.get(
            "WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki/self-wiki"
        )
    )

    # 1. Retrieval: Find relevant documents based on expanded query terms
    logger.info(f"Expanding query: {query}")
    query_terms = expand_query_terms(query)
    logger.info(f"Using search terms: {query_terms}")

    candidates = []
    # Recursively scan all files in the self-wiki folder
    for f in workspace.rglob("*.md"):
        # Exclude management files and specific directories
        if (
            f.name in ["INDEX.md", "audit.md"]
            or "outputs/" in str(f)
            or "raw/" in str(f)
        ):
            continue
        content = f.read_text(encoding="utf-8").lower()
        score = sum(1 for term in query_terms if term in content)
        if score > 0:
            candidates.append((score, f, content))

    # Sort by relevance
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_context = "\n".join(
        [f"--- {f.name} ---\n{content}" for score, f, content in candidates[:5]]
    )

    if top_context:
        print(f"top_context: {top_context}")
    else:
        print("No relevant information found.")
        return

    # 2. Augmentation: Synthesis via LLM
    llm_provider = os.environ.get("LLM_PROVIDER", "mlx").lower()
    llm_model = os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit")

    prompt = f"""
You are the "Second Brain" for a developer/thinker.
Use the following context to answer the user's question.

CONTEXT:
{top_context}

USER QUESTION:
{query}

CRITICAL RULES:
- Use the context to formulate an analytical and insightful answer.
- Always cite the source files using (Source: [[filename]]) format.
- Maintain the language of the query or the original source notes.
- If the answer is not in the context, say "I have no record of this in your data."
"""

    # Calling the LLM (reuse logic from sync_wiki.py)
    try:
        if llm_provider == "mlx":
            url = os.environ.get(
                "LLM_URL", "http://100.90.225.26:8080/v1/chat/completions"
            )
            payload = {
                "model": llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "stream": False,
            }
            response = requests.post(url, json=payload, timeout=300)
            answer = (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
        else:
            print("Only MLX provider supported for queries currently.")
            return

        print(f"\n--- ANSWER ---\n{answer}")

        # Auto-save the answer to outputs/
        from datetime import datetime

        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_filename = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]+", "-", query)[:50].strip(
            "-"
        )
        title = f"{safe_filename}-{date_str}.md"

        qa_dir = workspace / "outputs"
        qa_dir.mkdir(exist_ok=True)

        note_content = f"""
---
tags: #type/synthesis
---
# {title.replace(".md", "")}

Question: {query}

Answer:
{answer}
"""
        (qa_dir / title).write_text(note_content, encoding="utf-8")
        print(f"\nInsight automatically saved to {qa_dir / title}.")

    except Exception as e:
        logger.error(f"Error querying wiki: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/query_wiki.py "Your question"')
    else:
        query_wiki(sys.argv[1])
