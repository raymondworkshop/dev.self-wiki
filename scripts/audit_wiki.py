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

    # 2. Emotional Trigger Audit
    emotional_triggers = []
    # Identify patterns matching emotion indicators
    for item in file_list:
        content = item["content"]
        # Look for tag lines like "- emotion/..."
        matches = re.findall(r"- emotion/([a-zA-Z0-9_-]+)", content)
        if matches:
            # For each emotion, get context (a few lines around the match)
            for emotion in matches:
                # Find the line containing the emotion
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if f"emotion/{emotion}" in line:
                        # Grab some context (the line and maybe 1-2 lines before for "why")
                        context = " ".join(lines[max(0, i - 2) : i + 1]).strip()
                        emotional_triggers.append(
                            {
                                "emotion": emotion,
                                "context": context,
                                "path": str(item["path"]),
                            }
                        )

    # ... (Keep existing Contradiction Audit logic) ...

    # 4. Generate Report
    report = [
        "# Wiki Audit and Quality Review",
        f"**Last Automated Run**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n---",
        "\n### ⚖️ Cognitive Contradictions & Shifts",
        "\n".join(contradictions) if contradictions else "No contradictions found.",
        "\n### 🎭 Emotional Triggers & Shifts",
        "| Emotion | Context / Cause | File Path |",
        "| :--- | :--- | :--- |",
    ]
    for trigger in emotional_triggers:
        report.append(
            f"| {trigger['emotion']} | {trigger['context']} | `{trigger['path']}` |"
        )

    report.extend(
        [
            "\n### 🧠 AI Instructions",
            "1. Prioritize creating stubs for the high-frequency Red Links listed below.",
            "2. Reflect on the 'Socratic Questions' provided for each contradiction.",
            "\n### 🚨 Red Links (Missing topics, Frequency > 1)",
            "\n| Frequency | Topic |",
            "| :--- | :--- |",
        ]
    )

    red_link_counts = Counter(red_links).most_common()
    filtered_red_links = [item for item in red_link_counts if item[1] > 1]
    if not filtered_red_links:
        report.append("| - | No recurring red links found! |")
    else:
        for topic, count in filtered_red_links:
            report.append(f"| {count} | [[{topic}]] |")

    report.extend(
        [
            "\n### ⚠️ Structural Warnings",
            "\n".join(structural_warnings)
            if structural_warnings
            else "No structural warnings found.",
        ]
    )

    with open(audit_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    logger.info(f"Audit completed. Report updated at {audit_file}")
    print(f"Audit completed. Report updated at {audit_file}")


if __name__ == "__main__":
    run_audit()
