"""Apply ingest actions JSON to wiki pages (deterministic, zero LLM)."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from models import WikiPage
from wiki_themes import load_existing_themes

logger = logging.getLogger(__name__)


def apply_actions(data: dict, *, rel_path: str | None = None) -> int:
    """Merge actions into wiki. Returns number of pages updated."""
    _, title_to_path = load_existing_themes()
    updated = 0

    for action in data.get("actions", []):
        target_title = action.get("target_title")
        if not target_title:
            logger.warning("Skipping action without target_title")
            continue

        if target_title in title_to_path:
            page = WikiPage(title_to_path[target_title])
            logger.info("Merging into existing page: %s", title_to_path[target_title].name)
        else:
            level = int(action.get("level", 1))
            page = WikiPage.create_new(target_title, level=level)
            title_to_path[target_title] = page.file_path
            logger.info("Creating new page for theme: %s", target_title)

        page.front_matter["confidence"] = action.get("confidence_score", 1.0)
        page.front_matter["confidence_rationale"] = action.get(
            "confidence_rationale", ""
        )

        if action.get("bilingual_alias"):
            page.front_matter["alias"] = action["bilingual_alias"]

        if not page.summary and action.get("summary"):
            summary = re.sub(r"^(>\s*)+", "", action["summary"].strip())
            page.summary = summary

        if not page.front_matter.get("description") and action.get("description"):
            page.front_matter["description"] = action["description"]

        if action.get("level") is not None:
            existing_level = int(page.front_matter.get("level", 1) or 1)
            new_level = int(action["level"])
            page.front_matter["level"] = max(existing_level, new_level)
            tags = page.front_matter.get("tags", [])
            if not isinstance(tags, list):
                tags = [str(tags)]
            if existing_level >= 2 and "type/principle" in tags:
                page.front_matter["level"] = existing_level

        body_content = action.get("new_body_content", "")
        cleaned_body = "\n".join(
            re.sub(r"^>\s*", "", line) for line in body_content.splitlines()
        )
        source_rel = rel_path or data.get("raw_path") or "unknown"
        if source_rel.startswith("raw/"):
            source_rel = source_rel[len("raw/") :]
        if cleaned_body.strip() and cleaned_body.strip() not in page.body:
            page.body += (
                f"\n\n### Distillation ({datetime.now().strftime('%Y-%m-%d')})"
                f" - source: [[../raw/{source_rel}]]\n{cleaned_body}\n"
            )

        source_link = f"../raw/{source_rel}"
        if source_link not in page.sources:
            page.sources.append(source_link)

        evo_entry = (
            f"- {datetime.now().strftime('%Y-%m-%d')}: "
            f"Distilled from raw source [[{source_link}]]."
        )
        if evo_entry not in page.evolution:
            page.evolution = (page.evolution + "\n" + evo_entry).strip()

        current_tags = set(page.front_matter.get("tags", []))
        current_tags.update(action.get("tags", []))
        page.front_matter["tags"] = list(current_tags)
        page.save()
        updated += 1
        logger.info("Integrated theme: %s", target_title)

    return updated


def apply_from_file(actions_path: Path, *, rel_path: str | None = None) -> int:
    data = json.loads(actions_path.read_text(encoding="utf-8"))
    if "actions" not in data and actions_path.name.startswith("ingest-actions"):
        pass
    elif "actions" not in data:
        raise ValueError(f"No actions[] in {actions_path}")

    effective_rel = rel_path or data.get("raw_path")
    return apply_actions(data, rel_path=effective_rel)
