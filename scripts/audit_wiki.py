import logging
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_TOKENS = 8192  # local mlx
PROMPT_OVERHEAD = 2000  # Headroom for ongoing summary
WORKING_BUDGET = MAX_TOKENS - PROMPT_OVERHEAD


# Load .env
def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_env(Path(__file__).parent.parent / ".env")
workspace = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)


def get_yaml_field(content, field):
    match = re.search(rf"^{field}:\s*(.*)", content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return None


def call_llm(prompt: str, language: str = "Chinese"):
    url = os.environ.get("LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or "no-key"
    )
    model = os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit")
    system_prompt = f"You are a Socratic assistant helping the user audit their personal wiki. Always label your analysis with '[AI Synthesis]' and cite your sources with '[Source Evidence]'. Respond in {language}."
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=420)
        if response.status_code != 200:
            logger.error(f"LLM API Error: {response.text}")
            return "Audit failed (LLM API error)"
        return (
            response.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
    except Exception as e:
        return f"Contradiction audit failed: {e}"


def run_audit():
    logger.info("Starting wiki audit...")
    self_wiki_dir = workspace / "self-wiki"
    wiki_dir = self_wiki_dir / "wiki"
    audit_file = self_wiki_dir / "audit.md"

    # 1. Collect all content and topics
    wiki_files = []
    for f in wiki_dir.rglob("*.md"):
        if f.name in ["audit.md", "INDEX.md"] or f.name.endswith("-Hub.md"):
            continue
        wiki_files.append(f)

    # Sort files by level (Level 2 first)
    def get_level(f):
        try:
            content = f.read_text(encoding="utf-8")
            return int(get_yaml_field(content, "level") or 0)
        except:
            return 0

    wiki_files.sort(key=get_level, reverse=True)

    existing_topics = {f.stem for f in wiki_files}
    red_links, stale_files, emotional_triggers, structural_warnings = [], [], [], []

    # ... (Keep existing EMOTIONAL_PATTERNS and link logic) ...

    # 3. Contradiction Audit (LLM integration)
    contradictions = []
    language = "Chinese"

    # 1. BucketManager: Rank and group files by token budget
    def get_file_stats(f):
        content = f.read_text(encoding="utf-8")
        return {
            "path": f,
            "tokens": len(content) // 4,
            "content": content,
            "level": int(get_yaml_field(content, "level") or 0),
            "mtime": f.stat().st_mtime,
        }

    file_list = [get_file_stats(f) for f in wiki_files]
    # Sort: Level (high to low) then mtime (new to old)
    file_list.sort(key=lambda x: (x["level"], x["mtime"]), reverse=True)

    buckets = []
    current_bucket = []
    current_tokens = 0
    # MAX_TOKENS = 8192
    # PROMPT_OVERHEAD = 2000  # Headroom for ongoing summary
    # WORKING_BUDGET = MAX_TOKENS - PROMPT_OVERHEAD

    for item in file_list:
        if current_tokens + item["tokens"] > WORKING_BUDGET and current_bucket:
            buckets.append(current_bucket)
            logger.info(
                f"Created bucket with {len(current_bucket)} files ({current_tokens} tokens)"
            )
            current_bucket = []
            current_tokens = 0
        current_bucket.append(item)
        current_tokens += item["tokens"]
    if current_bucket:
        buckets.append(current_bucket)
        logger.info(
            f"Created final bucket with {len(current_bucket)} files ({current_tokens} tokens)"
        )
    logger.info(f"Total buckets created: {len(buckets)}")

    # 2. Sequential Reasoning with Running Summary
    running_summary = "None yet."
    for i, bucket in enumerate(buckets):
        logger.info(f"Processing reasoning bucket {i + 1}/{len(buckets)}...")
        bucket_text = "\n".join(
            [f"--- FILE: {item['path'].name} ---\n{item['content']}" for item in bucket]
        )
        prompt = f"""
        Analyze these wiki notes for contradictions or cognitive shifts compared to previous findings.

        Running Principle Summary: {running_summary}

        New Notes to Analyze:
        {bucket_text}

        Format: Contradiction: [desc]\nLabels: [AI Synthesis]... [Source Evidence]...\nSuggestion: [how to resolve].
        Update the 'Running Principle Summary' based on these findings.
        """

        result = call_llm(prompt, language)
        if result and "Audit failed" not in result:
            logger.info(f"Successfully processed bucket {i + 1} reasoning.")
            contradictions.append(result)
            if "Running Principle Summary:" in result:
                running_summary = result.split("Running Principle Summary:")[-1].strip()
        else:
            logger.error(f"Reasoning failed for bucket {i + 1}")

    # 3. Global Aggregation Pass
    if len(buckets) > 1:
        logger.info("Performing global aggregation pass...")
        agg_prompt = f"Consolidate these findings into a final report on logical contradictions across the entire wiki:\n\n{' '.join(contradictions)}"
        final_report = call_llm(agg_prompt, language)
        contradictions = [final_report]

    # 4. Generate Report
    # ... (Keep existing report generation logic) ...

    # Proactive Console Summary
    print("\n--- 🧠 Proactive Audit Summary ---")
    if contradictions:
        print(f"Found {len(contradictions)} potential contradictions/shifts.")
        print(contradictions[0][:300] + "...")
    else:
        print("No critical contradictions found.")
    print(f"Full report updated at: {audit_file}\n")


if __name__ == "__main__":
    run_audit()
