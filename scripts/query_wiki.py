import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_PATH = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)
INDEX_PATH = WORKSPACE_PATH / "self-wiki" / "log" / "INDEX.json"


def get_llm_response(prompt, system_prompt="You are a Socratic assistant."):
    url = os.environ.get("LLM_URL", "http://100.90.225.26:8080/v1/chat/completions")
    payload = {
        "model": os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    try:
        response = requests.post(url, json=payload, timeout=300)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return None


def get_query_keywords(query):
    # LLM translates and expands query into standard bilingual keywords
    prompt = f"Extract core keywords from the query: '{query}'. Provide them as a comma-separated list of Chinese and English equivalents. Only output the list, nothing else."
    response = get_llm_response(prompt, "You are a terminology extractor.")
    if response:
        return [t.strip() for t in response.split(",")]
    return query.lower().split()


def query_wiki(query):
    if query == "--list":
        with open(INDEX_PATH, "r") as f:
            index = json.load(f)
            print("Available topics:")
            print("\n".join(sorted(index["topics"].keys())))
        return

    if not INDEX_PATH.exists():
        logger.error("Index not found. Run 'make sync' first.")
        return
    with open(INDEX_PATH, "r") as f:
        index = json.load(f)

    # Synthesis Mode: Thematic Boost Ranking (Uses metadata from INDEX.json)
    ranked_files = []
    # Use LLM-extracted keywords instead of raw query terms
    query_terms = get_query_keywords(query)
    logger.info(f"Normalized query terms: {query_terms}")

    logger.info("Ranking wiki files based on query relevance and foundational level...")
    for name, data in index["topics"].items():
        f = WORKSPACE_PATH / data["path"]
        level = data.get("level", 0)
        tags = " ".join(data.get("tags", []))

        # Thematic Boost: +20 points for each query term match in name or tags
        match_boost = sum(
            20 for term in query_terms if term in name.lower() or term in tags.lower()
        )
        score = (level * 10) + match_boost

        ranked_files.append((score, f))

    ranked_files.sort(key=lambda x: x[0], reverse=True)
    top_3 = ranked_files[:3]
    logger.info(f"Selected top 3 files for synthesis: {[f.name for _, f in top_3]}")

    bucket = [f.read_text(encoding="utf-8") for _, f in top_3]

    logger.info("Synthesizing answer using LLM...")
    # Strict prompt requiring source citations
    prompt = f"""Synthesize the following principles and content into a comprehensive response answering: {query}

    Context: {" ".join(bucket)}

    CRITICAL INSTRUCTION: For every insight provided, you MUST include its source using the format (Source: [[filename]]).

    Format:
    [AI Synthesis]: Your analysis here.
    [Source Evidence]: Provide clear citations for every claim.
    """

    answer = get_llm_response(
        prompt,
        "You are a Socratic analyst. Always provide synthesized reasoning based on your Principles and cite your sources using (Source: [[filename]]) for every insight.",
    )
    logger.info("Synthesis complete.")
    print(f"\n--- SYNTHESIS REPORT ---\n{answer}")

    # Auto-save the answer to self-wiki/outputs/
    qa_dir = WORKSPACE_PATH / "self-wiki" / "outputs"
    qa_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_query = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]+", "-", query)[:50].strip("-")
    filename = f"{safe_query}-{date_str}.md"

    note_content = f"""
---
tags: #type/synthesis
date: {date_str}
---
# {query}

{answer}
"""
    (qa_dir / filename).write_text(note_content, encoding="utf-8")
    logger.info(f"Insight automatically saved to {qa_dir / filename}.")
    print(f"\nInsight automatically saved to {qa_dir / filename}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/query_wiki.py "Your question"')
    else:
        query_wiki(sys.argv[1])
