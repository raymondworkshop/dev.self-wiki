import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path


def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


# Load .env
load_env(Path(__file__).parent.parent / ".env")
workspace = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)


def get_yaml_field(content, field):
    match = re.search(rf"^{field}:\s*(.*)", content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return None


def run_audit():
    self_wiki_dir = workspace / "self-wiki"
    wiki_dir = self_wiki_dir / "wiki"
    audit_file = self_wiki_dir / "audit.md"

    # 1. Get all existing topics
    # Scan all .md files in all subdirectories, excluding top-level hubs/index/audit
    existing_topics = {
        f.stem
        for f in wiki_dir.rglob("*.md")
        if f.name not in ["audit.md", "INDEX.md"] and not f.name.endswith("-Hub.md")
    }

    red_links = []
    stale_files = []
    link_pattern = re.compile(r"\[\[(.*?)\]\]")

    # 2. Scan files for links and staleness
    for file_path in wiki_dir.rglob("*.md"):
        if file_path.name in ["audit.md", "INDEX.md"]:
            continue

        content = file_path.read_text(encoding="utf-8")

        # Check links
        links = link_pattern.findall(content)
        for link in links:
            clean_link = link.split("|")[0].strip()
            if clean_link not in existing_topics:
                red_links.append(clean_link)

        # Check staleness
        last_updated_str = get_yaml_field(content, "last_updated")
        if last_updated_str:
            try:
                # Handle ISO format
                last_updated = datetime.fromisoformat(
                    last_updated_str.replace("Z", "+00:00")
                )
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(
                        tzinfo=datetime.now().astimezone().tzinfo
                    )

                days_diff = (datetime.now(last_updated.tzinfo) - last_updated).days
                if days_diff > 60:
                    stale_files.append((file_path.name, days_diff))
            except ValueError:
                continue

    # 3. Aggregate Red Links
    red_link_counts = Counter(red_links).most_common()

    # 4. Perform Contradiction Audit via script
    contradictions = ""
    try:
        result = subprocess.run(
            ["python3", str(workspace / "scripts/audit_contradictions.py")],
            capture_output=True,
            text=True,
        )
        contradictions = result.stdout
    except Exception as e:
        contradictions = f"Could not perform contradiction audit: {e}"

    # 5. Generate Audit Report
    report = [
        "# Wiki Audit and Quality Review",
        f"**Last Automated Run**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n---",
        "\n### 🚨 Red Links (Empty topics frequently mentioned)",
        "\n| Frequency | Topic |",
        "| :--- | :--- |",
    ]

    if not red_link_counts:
        report.append("| 0 | No red links found! |")
    for topic, count in red_link_counts:
        report.append(f"| {count} | [[{topic}]] |")

    report.append("\n### ⏳ Stale Information (>60 days)")
    if not stale_files:
        report.append("All files are up to date.")
    else:
        for name, days in stale_files:
            report.append(f"- `{name}`: {days} days since last update.")

    report.append("\n### ⚖️ Cognitive Contradictions & Shifts")
    report.append(
        contradictions if contradictions.strip() else "No contradictions found."
    )

    report.extend(
        [
            "\n### 🧠 AI Instructions for Next Sync",
            "1. Prioritize creating stubs for the high-frequency Red Links listed above.",
            "2. Analyze `raw/` for content matching these topics.",
            "3. Review identified 'Cognitive Shifts' and update corresponding notes with `#contradiction` tags.",
        ]
    )

    with open(audit_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"Audit completed. Report updated at {audit_file}")


if __name__ == "__main__":
    run_audit()
