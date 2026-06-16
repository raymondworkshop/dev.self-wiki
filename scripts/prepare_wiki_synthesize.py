"""Build pending JSON for wiki-synthesize (compression → wiki actions)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from config import PENDING_DIR, WORKSPACE_PATH, workspace_relpath
from ingest_profiles import resolve_profile
from lang_utils import detect_language, language_output_instruction
from skill_registry import resolve_skill
from wiki_synth_manifest import compression_to_raw_rel, _raw_rel_from_compression
from wiki_themes import load_existing_themes

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
THEME_LINKS_SECTION_RE = re.compile(
    r"^## Theme links\s*\n(.*?)(?:\n## |\Z)", re.MULTILINE | re.DOTALL
)
CONFIDENCE_IN_THEME_RE = re.compile(r"\(confidence:\s*([0-9.]+)\)", re.IGNORECASE)


def _sanitize_slug(comp_rel: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", comp_rel).strip("-")
    return slug[:80] or "compression"


def _parse_theme_links(content: str) -> list[tuple[str, float | None]]:
    m = THEME_LINKS_SECTION_RE.search(content)
    if not m:
        return []
    titles: list[tuple[str, float | None]] = []
    for line in m.group(1).splitlines():
        link = WIKI_LINK_RE.search(line)
        if not link:
            continue
        title = link.group(1).strip()
        conf_m = CONFIDENCE_IN_THEME_RE.search(line)
        conf = float(conf_m.group(1)) if conf_m else None
        titles.append((title, conf))
    return titles


def _wiki_excerpt(title: str, title_to_path: dict, *, max_chars: int = 4000) -> str:
    path = title_to_path.get(title)
    if not path or not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + "\n… (truncated)"
    return text


def build_user_message(
    *,
    comp_rel: str,
    content: str,
    max_theme_updates: int,
    skill_rel: str,
) -> str:
    raw_path = compression_to_raw_rel(comp_rel)
    source_lang = detect_language(content)
    themes, title_to_path = load_existing_themes()
    theme_titles = _parse_theme_links(content)

    titles_context = "\n".join(
        f"- {t['title']}" + (f" (alias: {t['alias']})" if t.get("alias") else "")
        for t in themes[:200]
    )

    matched_excerpts: list[str] = []
    seen_titles: set[str] = set()
    for title, _conf in theme_titles:
        if title in seen_titles:
            continue
        excerpt = _wiki_excerpt(title, title_to_path)
        if excerpt:
            matched_excerpts.append(f"### Wiki page: {title}\n{excerpt}")
            seen_titles.add(title)

    parts = [
        "Execute the wiki-synthesize skill for this compression digest.",
        language_output_instruction(source_lang),
        f"Compression path: {comp_rel}",
        f"Raw path: {raw_path}",
        f"max_theme_updates: {max_theme_updates}",
        f"Skill: {skill_rel}",
        "",
        "Existing wiki themes:",
        titles_context or "(none)",
        "",
    ]

    if theme_titles:
        parts.append("Theme links from digest (prefer these targets):")
        for title, conf in theme_titles:
            conf_s = f" confidence≥{conf}" if conf is not None else ""
            parts.append(f"- [[{title}]]{conf_s}")
        parts.append("")

    if matched_excerpts:
        parts.append("Matched wiki page excerpts:")
        parts.extend(matched_excerpts)
        parts.append("")

    parts.extend(["Compression digest:", "---", content, "---"])
    return "\n".join(parts)


def write_pending(comp_path: Path) -> Path | None:
    comp_rel = workspace_relpath(comp_path)
    raw_rel = _raw_rel_from_compression(comp_rel)
    profile = resolve_profile(raw_rel)
    if not profile or not profile.get("wiki_skill"):
        return None

    max_updates = int(profile.get("max_theme_updates", 0) or 0)
    if max_updates <= 0:
        return None

    content = comp_path.read_text(encoding="utf-8", errors="ignore")
    skill_rel = resolve_skill(
        "wiki_synthesize",
        profile["wiki_skill"],
        raw_rel=raw_rel,
        current_skill=profile.get("wiki_skill"),
    )
    user_message = build_user_message(
        comp_rel=comp_rel,
        content=content,
        max_theme_updates=max_updates,
        skill_rel=skill_rel,
    )

    slug = _sanitize_slug(comp_rel)
    pending_path = PENDING_DIR / f"wiki-synth-{slug}.json"
    payload = {
        "kind": "ingest",
        "skill": skill_rel,
        "compression_path": comp_rel,
        "raw_path": compression_to_raw_rel(comp_rel),
        "max_theme_updates": max_updates,
        "user_message": user_message,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actions_output": f"wiki-synth-actions-{slug}.json",
    }
    pending_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return pending_path
