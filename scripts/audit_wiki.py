import logging
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml
from llm_provider import call_llm

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Load .env
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
workspace = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)

def run_audit():
    logger.info("Starting wiki audit...")
    self_wiki_dir = workspace / "self-wiki"
    wiki_dir = self_wiki_dir / "wiki"
    audit_file = self_wiki_dir / "audit.md"

    if not wiki_dir.exists():
        logger.error(f"Wiki directory not found: {wiki_dir}")
        return

    wiki_files = list(wiki_dir.rglob("*.md"))

    # 1. Data Collection
    pages_data = []
    all_titles = set()
    for f in wiki_files:
        if f.name in ["audit.md", "INDEX.md"] or f.name.endswith("-Hub.md"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            pages_data.append(
                {
                    "path": f,
                    "rel_path": f.relative_to(workspace),
                    "content": content,
                    "title": f.stem,
                }
            )
            all_titles.add(f.stem)
        except Exception as e:
            logger.error(f"Error reading {f}: {e}")

    # 2. Audits
    red_links = []
    emotional_triggers = []
    contradictions = []
    structural_warnings = []

    for page in pages_data:
        content = page["content"]

        # 2. Structural Audit (GEMINI Standards)
        missing_sections = []
        if not re.search(r"^>\s", content, re.MULTILINE):
            missing_sections.append("Socratic Summary (`>`)")
        if "## Evolution" not in content:
            missing_sections.append("Evolution Section")
        if "## Sources" not in content:
            missing_sections.append("Sources Section")

        if missing_sections:
            structural_warnings.append(
                f"#### [[{page['title']}]]\n- Missing: {', '.join(missing_sections)}"
            )

        # Red Links Audit
        links = re.findall(r"\[\[(.*?)\]\]", content)
        for link in links:
            link_clean = link.split("|")[0].split("#")[0].strip()
            if link_clean and link_clean not in all_titles:
                red_links.append(link_clean)

        # Emotional Trigger Audit
        # Look for tag lines like "- emotion/..." or explicit mentions
        emotion_matches = re.findall(r"emotion/([a-zA-Z0-9_-]+)", content)
        for emotion in emotion_matches:
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if f"emotion/{emotion}" in line:
                    context = " ".join(lines[max(0, i - 1) : i + 2]).strip()
                    emotional_triggers.append(
                        {
                            "emotion": emotion,
                            "context": context,
                            "path": page["rel_path"],
                        }
                    )
                    break

        # LLM Audit (Cognitive Shifts / Contradictions)
        # We only do this for Level 2 or high-value files to save time
        level = int(get_yaml_field(content, "level") or 0)
        if level >= 1:
            logger.info(f"LLM Auditing {page['title']}...")
            sys_prompt = (
                "You are a Socratic Auditor, acting as a 'Socratic Mirror'. Your duty is to identify 'Emotional Triggers', "
                "'Cognitive Shifts' (contradictions), and 'Stale Wisdom'. "
                "If raising a reflective challenge, label it [Socratic Observation]. "
                "Respond in the same language as the input."
            )
            audit_prompt = (
                f"Audit this wiki entry: [[{page['title']}]]\n\n"
                "Focus on identifying patterns that contradict other principles or reveal underlying anxieties. "
                "End with a heuristic 'Socratic Question' to elicit the user's bottom-level logic.\n\n"
                f"Content:\n{content[:2000]}"
            )
            res = call_llm(audit_prompt, sys_prompt)
            if res and "PASS" not in res.upper():
                contradictions.append(f"#### [[{page['title']}]]\n{res}")

    # 3. Generate Report
    report = [
        "# Wiki Audit & Socratic Mirror Report",
        f"**Last Run**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n> This report scans for cognitive shifts, emotional patterns, and structural fidelity to the GEMINI.md standards.",
        "\n---",
        "\n### ⚖️ Cognitive Shifts & [Socratic Observations]",
        "\n\n".join(contradictions)
        if contradictions
        else "No significant cognitive shifts identified.",
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

    audit_file.write_text("\n".join(report), encoding="utf-8")
    logger.info(f"Audit completed. Report updated at {audit_file}")


if __name__ == "__main__":
    run_audit()
