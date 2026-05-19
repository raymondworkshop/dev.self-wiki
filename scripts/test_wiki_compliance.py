import os
import re
import sys
from pathlib import Path


def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


# Load .env
load_env(Path(__file__).parent.parent / ".env")
WORKSPACE_PATH = Path(
    os.environ.get(
        "WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki/self-wiki"
    )
)


def check_compliance():
    wiki_root = WORKSPACE_PATH
    md_files = [
        f
        for f in wiki_root.rglob("*.md")
        if f.name not in ["INDEX.md", "audit.md"] and not f.name.endswith("-Hub.md")
    ]

    errors = []

    required_fields = ["last_updated", "title", "description", "tags"]

    for f in md_files:
        content = f.read_text(encoding="utf-8")

        # Check YAML Front Matter
        match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            errors.append(f"{f.name}: Missing YAML front matter.")
            continue

        front_matter = match.group(1)
        for field in required_fields:
            if not re.search(rf"^{field}:", front_matter, re.MULTILINE):
                errors.append(f"{f.name}: Missing front matter field '{field}'.")

        # Check Evolution
        if "## Evolution" not in content:
            errors.append(f"{f.name}: Missing '## Evolution' section.")

        # Check for Sources section
        if not re.search(r"##\s+sources", content, re.IGNORECASE):
            errors.append(f"{f.name}: Missing '## Sources' section.")

        # Check for 2-3 sentence summary after front matter
        # Front matter is detected by the closing '---'
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
            # Split by double newline to find the first paragraph/block
            first_block = body.split("\n\n")[0].strip()
            # Simple sentence counting
            sentences = re.split(r"[.!?]+", first_block)
            sentences = [s for s in sentences if s.strip()]
            if not (2 <= len(sentences) <= 3):
                errors.append(
                    f"{f.name}: Summary should be 2-3 sentences. Found {len(sentences)} sentences."
                )
        else:
            errors.append(f"{f.name}: Could not extract body for summary check.")

    if errors:
        print("Compliance Check Failed:")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)
    else:
        print("Compliance Check Passed: All wiki files meet GEMINI requirements.")
        sys.exit(0)


if __name__ == "__main__":
    check_compliance()
