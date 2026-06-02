"""Deterministic wiki audit (no per-page LLM). Use `make lint` for global cognitive lint."""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from config import AUDIT_MD, WIKI_DIR, WORKSPACE_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_yaml_field(content: str, field: str) -> str | None:
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    meta = yaml.safe_load(parts[1]) or {}
    val = meta.get(field)
    return str(val) if val is not None else None


def get_yaml_tags(content: str) -> list[str]:
    if not content.startswith("---"):
        return []
    parts = content.split("---", 2)
    if len(parts) < 3:
        return []
    meta = yaml.safe_load(parts[1]) or {}
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        return [tags]
    return [str(t) for t in tags]


def _primary_theme_tag(tags: list[str]) -> str | None:
    for tag in tags:
        if tag.startswith("type/"):
            return tag
    for tag in tags:
        if tag.startswith("domain/") or tag.startswith("theme/"):
            return tag
    return tags[0] if tags else None


def find_duplicate_themes(
    pages_data: list[dict],
    *,
    threshold: float = 0.88,
    tag_threshold: float = 0.82,
) -> list[str]:
    warnings: list[str] = []
    titles = [p["title"] for p in pages_data]
    seen: set[tuple[str, str]] = set()

    for i, t1 in enumerate(titles):
        for t2 in titles[i + 1 :]:
            if t1 == t2:
                continue
            ratio = SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
            if ratio < threshold:
                continue
            pair = tuple(sorted([t1, t2]))
            if pair in seen:
                continue
            seen.add(pair)
            warnings.append(
                f"- Similar titles ({ratio:.0%}): [[{t1}]] ↔ [[{t2}]]"
            )

    by_tag: dict[str, list[dict]] = {}
    for page in pages_data:
        tag = _primary_theme_tag(page.get("tags") or [])
        if not tag:
            continue
        by_tag.setdefault(tag, []).append(page)

    for tag, cluster in sorted(by_tag.items()):
        if len(cluster) < 2:
            continue
        cluster_titles = [p["title"] for p in cluster]
        for i, t1 in enumerate(cluster_titles):
            for t2 in cluster_titles[i + 1 :]:
                if t1 == t2:
                    continue
                ratio = SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
                if ratio < tag_threshold:
                    continue
                pair = tuple(sorted([t1, t2]))
                if pair in seen:
                    continue
                seen.add(pair)
                warnings.append(
                    f"- Same tag `{tag}` + similar titles ({ratio:.0%}): "
                    f"[[{t1}]] ↔ [[{t2}]]"
                )

    return warnings


def collect_level2_soft_warnings(pages_data: list[dict]) -> list[str]:
    """Advisory only — does not fail compliance tests on existing corpus."""
    warnings: list[str] = []
    for page in pages_data:
        content = page["content"]
        level_raw = get_yaml_field(content, "level")
        try:
            level = int(level_raw or 0)
        except (TypeError, ValueError):
            level = 0
        if level < 2:
            continue

        title = page["title"]
        tags = get_yaml_tags(content)
        tag_blob = " ".join(tags)
        conf_raw = get_yaml_field(content, "confidence")
        try:
            confidence = float(conf_raw or 0)
        except (TypeError, ValueError):
            confidence = 0.0

        if "type/principle" not in tag_blob:
            warnings.append(
                f"- [[{title}]]: Level 2 without `type/principle` tag"
            )
        if confidence < 0.7:
            conf_label = conf_raw if conf_raw else "missing"
            warnings.append(
                f"- [[{title}]]: Level 2 confidence {conf_label} (< 0.7 twin floor)"
            )
        if not get_yaml_field(content, "confidence_rationale"):
            warnings.append(
                f"- [[{title}]]: Level 2 missing `confidence_rationale`"
            )

    return warnings


def run_audit() -> None:
    logger.info("Starting deterministic wiki audit...")
    wiki_dir = WIKI_DIR
    audit_file = AUDIT_MD

    if not wiki_dir.exists():
        logger.error("Wiki directory not found: %s", wiki_dir)
        return

    wiki_files = list(wiki_dir.rglob("*.md"))
    pages_data = []
    all_titles: set[str] = set()

    for f in wiki_files:
        if f.name in ["audit.md", "INDEX.md"] or f.name.endswith("-Hub.md"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            pages_data.append(
                {
                    "path": f,
                    "rel_path": f.relative_to(WORKSPACE_PATH),
                    "content": content,
                    "title": f.stem,
                    "tags": get_yaml_tags(content),
                }
            )
            all_titles.add(f.stem)
        except OSError as exc:
            logger.error("Error reading %s: %s", f, exc)

    red_links: list[str] = []
    emotional_triggers: list[dict] = []
    structural_warnings: list[str] = []

    for page in pages_data:
        content = page["content"]

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

        links = re.findall(r"\[\[(.*?)\]\]", content)
        for link in links:
            link_clean = link.split("|")[0].split("#")[0].strip()
            if link_clean and link_clean not in all_titles:
                red_links.append(link_clean)

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

    duplicate_warnings = find_duplicate_themes(pages_data)
    level2_warnings = collect_level2_soft_warnings(pages_data)

    report = [
        "# Wiki Audit & Socratic Mirror Report",
        f"**Last Run**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n> Deterministic scan: structure, red links, emotional tags, duplicate themes, Level-2 guidance.",
        "\n> For cross-page cognitive lint, run `make lint` (one global LLM pass via skills/lint.md).",
        "\n---",
        "\n### ⚖️ Cognitive Shifts & [Socratic Observations]",
        "\n_Run `make lint` to populate global cognitive lint (replaces per-page LLM audit)._",
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
            "\n### 🔁 Duplicate / Near-Duplicate Themes",
            "\n".join(duplicate_warnings)
            if duplicate_warnings
            else "No near-duplicate titles detected.",
            "\n### 📐 Level-2 soft guidance (advisory)",
            "\n".join(level2_warnings[:40])
            if level2_warnings
            else "No Level-2 guidance items.",
            *(
                [f"\n_… and {len(level2_warnings) - 40} more Level-2 items._"]
                if len(level2_warnings) > 40
                else []
            ),
            "\n### ⚠️ Structural Warnings",
            "\n".join(structural_warnings)
            if structural_warnings
            else "No structural warnings found.",
        ]
    )

    audit_file.parent.mkdir(parents=True, exist_ok=True)
    audit_file.write_text("\n".join(report), encoding="utf-8")
    logger.info("Audit completed. Report updated at %s", audit_file)


if __name__ == "__main__":
    run_audit()
