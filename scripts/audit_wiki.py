import os
import re
from pathlib import Path
from collections import Counter
from datetime import datetime
#import yaml

def run_audit():
    workspace = Path("/Users/zhaowenlong/workspace/dev.self-wiki")
    wiki_dir = workspace / "wiki"
    audit_file = wiki_dir / "audit.md"
    
    # 1. Get all existing topics
    existing_topics = {f.stem for f in wiki_dir.glob("*.md")}
    
    red_links = []
    link_pattern = re.compile(r"\[\[(.*?)\]\]")
    
    # 2. Scan files for links
    for file_path in wiki_dir.glob("*.md"):
        if file_path.name in ["audit.md", "INDEX.md"]:
            continue
            
        content = file_path.read_text(encoding='utf-8')
        links = link_pattern.findall(content)
        
        for link in links:
            # Clean link name (e.g., handle [[topic|alias]])
            clean_link = link.split('|')[0].strip()
            if clean_link not in existing_topics:
                red_links.append(clean_link)

    # 2b. Check for Stale Info (>60 days)
    """
    stale_files = []
    for file_path in wiki_dir.glob("*.md"):
        try:
            content = file_path.read_text()
            if "---" in content:
                fm = list(yaml.safe_load_all(content))[0]
                last_updated = datetime.fromisoformat(fm['last_updated'].replace('Z', '+00:00'))
                days_diff = (datetime.now(last_updated.tzinfo) - last_updated).days
                if days_diff > 60:
                    stale_files.append((file_path.name, days_diff))
        except Exception:
            # Skip files with malformed frontmatter during audit
            continue
    """

    # 3. Aggregate Red Links
    red_link_counts = Counter(red_links).most_common()

    # 4. Generate Audit Report
    report = [
        "# Wiki Audit and Quality Review",
        f"**Last Automated Run**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n---",
        "\n### 🚨 Red Links (Empty topics frequently mentioned)",
        "These topics are linked but do not have a corresponding file in `wiki/`. High frequency suggests a knowledge gap that needs filling.",
        "\n| Frequency | Topic |",
        "| :--- | :--- |"
    ]

    if not red_link_counts:
        report.append("| 0 | No red links found! |")
    for topic, count in red_link_counts:
        report.append(f"| {count} | [[{topic}]] |")

    
    report.append("\n### ⏳ Skip the Stale Information (>60 days)")
    """
    if not stale_files:
        report.append("All files are up to date.")
    for name, days in stale_files:
        report.append(f"- `{name}`: {days} days since last update.")
    """

    report.extend([
        "\n### 🧠 AI Instructions for Next Sync",
        "1. Prioritize creating stubs for the high-frequency Red Links listed above.",
        "2. Analyze `raw/` for content matching these topics.",
        "3. Look for 'Cognitive Shifts' where new data contradicts the current Wiki state."
    ])

    # 5. Write to audit.md
    with open(audit_file, "w", encoding='utf-8') as f:
        f.write("\n".join(report))
    print(f"Audit completed. Report updated at {audit_file}")

if __name__ == "__main__":
    run_audit()