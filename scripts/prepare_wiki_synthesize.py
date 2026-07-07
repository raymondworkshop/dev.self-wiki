"""Build pending JSON for wiki-synthesize (raw → wiki actions)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from config import PENDING_DIR, workspace_relpath
from ingest_profiles import resolve_profile
from lang_utils import detect_language, language_output_instruction
from raw_chunking import iter_units
from skill_registry import resolve_skill
from wiki_synth_manifest import raw_rel_inner
from wiki_themes import load_existing_themes

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
THEME_LINKS_SECTION_RE = re.compile(
    r"^## Theme links\s*\n(.*?)(?:\n## |\Z)", re.MULTILINE | re.DOTALL
)
CONFIDENCE_IN_THEME_RE = re.compile(r"\(confidence:\s*([0-9.]+)\)", re.IGNORECASE)


def _sanitize_slug(raw_rel: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw_rel).strip("-")
    return slug[:80] or "raw"


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
    raw_rel: str,
    content: str,
    max_theme_updates: int,
    skill_rel: str,
    unit_id: str | None = None,
) -> str:
    inner = raw_rel_inner(raw_rel)
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

    provenance = f"raw/{unit_id}" if unit_id and unit_id != inner else raw_rel
    parts = [
        "Execute the wiki-synthesize skill for this raw source.",
        language_output_instruction(source_lang),
        f"Raw path: {raw_rel}",
        f"Provenance: (Source: [[{provenance}]])",
        f"max_theme_updates: {max_theme_updates}",
        f"Skill: {skill_rel}",
        "",
        "Existing wiki themes:",
        titles_context or "(none)",
        "",
    ]

    if theme_titles:
        parts.append("Theme links from source (prefer these targets):")
        for title, conf in theme_titles:
            conf_s = f" confidence≥{conf}" if conf is not None else ""
            parts.append(f"- [[{title}]]{conf_s}")
        parts.append("")

    if matched_excerpts:
        parts.append("Matched wiki page excerpts:")
        parts.extend(matched_excerpts)
        parts.append("")

    parts.extend(["Raw source:", "---", content, "---"])
    return "\n".join(parts)


def write_pending(raw_path: Path, *, unit_id: str | None = None, content: str | None = None) -> Path | None:
    raw_rel = workspace_relpath(raw_path)
    inner = raw_rel_inner(raw_rel)
    profile = resolve_profile(inner)
    if not profile or not profile.get("wiki_skill"):
        return None

    max_updates = int(profile.get("max_theme_updates", 0) or 0)
    if max_updates <= 0:
        return None

    if content is None:
        content = raw_path.read_text(encoding="utf-8", errors="ignore")

    skill_rel = resolve_skill(
        "wiki_synthesize",
        profile["wiki_skill"],
        raw_rel=inner,
        current_skill=profile.get("wiki_skill"),
    )
    user_message = build_user_message(
        raw_rel=raw_rel,
        content=content,
        max_theme_updates=max_updates,
        skill_rel=skill_rel,
        unit_id=unit_id,
    )

    slug = _sanitize_slug(f"{raw_rel}-{unit_id}" if unit_id else raw_rel)
    pending_path = PENDING_DIR / f"wiki-synth-{slug}.json"
    payload = {
        "kind": "ingest",
        "skill": skill_rel,
        "raw_path": raw_rel,
        "unit_id": unit_id,
        "max_theme_updates": max_updates,
        "user_message": user_message,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actions_output": f"wiki-synth-actions-{slug}.json",
    }
    pending_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return pending_path


def write_pending_units(raw_path: Path) -> list[Path]:
    """Create pending package(s) for raw file, chunking if needed."""
    inner = raw_rel_inner(workspace_relpath(raw_path))
    units = iter_units(inner, raw_path)
    pending_paths: list[Path] = []
    for unit_id, chunk_content in units:
        p = write_pending(raw_path, unit_id=unit_id if len(units) > 1 else None, content=chunk_content)
        if p:
            pending_paths.append(p)
    return pending_paths
