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


def query_wiki(query):
    workspace = Path(__file__).parent.parent.resolve()
    wiki_dir = workspace / "wiki"

    # 1. Retrieval: Find relevant documents based on keyword overlap
    query_terms = set(query.lower().split())
    candidates = []
    for f in wiki_dir.glob("*.md"):
        if f.name in ["INDEX.md", "audit.md"]:
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

    if not top_context:
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
            url = os.environ.get("LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")
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

        note_content = f"""---
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
