import logging
import os
import re
from datetime import datetime
from pathlib import Path

import yaml
from config import WIKI_DIR

logger = logging.getLogger(__name__)


class WikiPage:
    """Model representing a single wiki page following GEMINI.md standards."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = ""
        self.front_matter = {}
        self.summary = ""
        self.evolution = ""
        self.body = ""
        self.backlinks = ""
        self.sources = []

        if self.file_path.exists():
            self.load()

    def load(self):
        content = self.file_path.read_text(encoding="utf-8")
        self.content = content

        # Parse YAML
        fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            try:
                self.front_matter = yaml.safe_load(fm_match.group(1))
            except yaml.YAMLError:
                self.front_matter = {}
            body_plus = content[fm_match.end() :].strip()
        else:
            body_plus = content.strip()

        # Parse Socratic Summary (starts with >)
        summary_match = re.search(r"^>\s*(.*?)(?=\n\n|\n##)", body_plus, re.DOTALL)
        if summary_match:
            self.summary = summary_match.group(1).strip()
            remaining = body_plus[summary_match.end() :].strip()
        else:
            remaining = body_plus

        # Parse Sections
        sections = re.split(r"\n##\s+", remaining)
        self.body = sections[0].strip()

        for section in sections[1:]:
            title_match = re.match(r"^(.*?)\n", section)
            if not title_match:
                continue

            title = title_match.group(1).strip().lower()
            content = section[title_match.end() :].strip()

            if "evolution" in title:
                self.evolution = content
            elif "backlinks" in title:
                self.backlinks = content
            elif "sources" in title:
                self.sources = [
                    line.strip("- ").strip("[]")
                    for line in content.splitlines()
                    if line.strip()
                ]

    def save(self):
        # Update last_updated
        self.front_matter["last_updated"] = datetime.now().isoformat()

        fm_str = yaml.dump(self.front_matter, sort_keys=False).strip()

        source_str = "\n".join([f"- [[{s}]]" for s in sorted(list(set(self.sources)))])

        full_content = f"""---
{fm_str}
---

> {self.summary}

{self.body}

## Evolution
{self.evolution}

## Backlinks
{self.backlinks}

## Sources
{source_str}
"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(full_content.strip() + "\n", encoding="utf-8")

    @classmethod
    def create_new(cls, title: str, level: int = 1):
        # Sanitize title for filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)  # Remove invalid chars
        safe_title = safe_title.replace(" ", "_").replace(":", "-")
        filename = f"{safe_title}.md"
        path = WIKI_DIR / filename

        # If file exists, load it; otherwise, initialize new
        page = cls(path)
        if not page.front_matter:
            page.front_matter = {
                "title": title,
                "last_updated": datetime.now().isoformat(),
                "description": "",
                "level": level,
                "tags": [],
            }
        return page
