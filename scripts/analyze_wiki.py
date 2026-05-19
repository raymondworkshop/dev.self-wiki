import collections
import re
from pathlib import Path


def analyze_wiki_distribution():
    workspace = Path("/Users/zhaowenlong/workspace/dev.self-wiki")
    wiki_dir = workspace / "wiki"

    tag_counts = collections.defaultdict(list)

    for wiki_file in wiki_dir.glob("*.md"):
        if wiki_file.name in ["INDEX.md", "audit.md"]:
            continue

        content = wiki_file.read_text(encoding="utf-8")

        # Extract tags from YAML front matter
        tags = []
        match = re.search(r"tags:\s*\[(.*?)\]", content)
        if match:
            tags = [t.strip().strip("'").strip('"') for t in match.group(1).split(",")]
        else:
            block_match = re.search(r"tags:\s*\n([\s\S]*?)\n---", content)
            if block_match:
                tags = [
                    re.sub(r"^-\s*", "", line).strip().strip("'").strip('"')
                    for line in block_match.group(1).splitlines()
                    if line.strip().startswith("-")
                ]

        for tag in tags:
            tag = tag.strip().replace("#", "")
            if tag:
                tag_counts[tag].append(wiki_file.stem)

    # Print report
    print("--- Wiki Theme Distribution Report ---")
    sorted_tags = sorted(tag_counts.items(), key=lambda x: len(x[1]), reverse=True)

    for tag, files in sorted_tags:
        print(f"Tag: {tag} ({len(files)} files)")
        if len(files) > 8:
            print("  [建议重构] 此主题文件较多，建议整理为枢纽页面。")
        for f in files[:5]:  # Show first 5
            print(f"  - {f}")
        if len(files) > 5:
            print(f"  ... (共 {len(files)} 个文件)")


if __name__ == "__main__":
    analyze_wiki_distribution()
