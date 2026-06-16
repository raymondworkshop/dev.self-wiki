"""Build pending compression packages (deterministic, zero LLM)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from config import COMPRESSION_DIR, PENDING_DIR, WORKSPACE_PATH
from ingest_profiles import resolve_profile
from lang_utils import detect_language, epistemic_label_instruction, language_output_instruction
from skill_registry import resolve_skill
from wiki_themes import load_existing_themes


def _sanitize_slug(rel_path: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", rel_path).strip("-")
    return slug[:80] or "source"


def build_compress_user_message(
    rel_path: str,
    content: str,
    *,
    skill_rel: str,
    is_chunk: bool = False,
) -> str:
    source_lang = detect_language(content)
    chunk_note = " (chunk of larger file)" if is_chunk else ""
    parts = [
        f"Raw path: raw/{rel_path.lstrip('raw/')}{chunk_note}",
        language_output_instruction(source_lang),
        epistemic_label_instruction(),
        f"Skill: {skill_rel}",
        "",
        "---",
        content,
        "---",
    ]
    if "ingest-thoughts" in skill_rel:
        themes, _ = load_existing_themes()
        if themes:
            titles = "\n".join(f"- {t['title']}" for t in themes[:200])
            parts.insert(
                4,
                f"Existing wiki themes (link only if explicit match, conf≥0.9):\n{titles}\n",
            )
    return "\n".join(parts)


def compression_output_path(rel_path: str) -> Path:
    """Map raw/_posts/foo.md → compression/_posts/foo.md"""
    if rel_path.startswith("raw/"):
        rel_path = rel_path[len("raw/") :]
    return COMPRESSION_DIR / rel_path


def prepare_for_unit(
    *,
    raw_rel: str,
    chunk_rel: str,
    content: str,
    file_hash: str,
    is_chunk: bool = False,
) -> list[Path]:
    profile = resolve_profile(raw_rel)
    if profile is None or profile.get("mode") == "reference":
        return []

    profile_skill = profile.get("skill")
    skill_rel = resolve_skill(
        "compression",
        profile_skill or "",
        raw_rel=raw_rel,
        current_skill=profile_skill,
    )
    if not skill_rel:
        return []

    source_lang = detect_language(content)
    user_message = build_compress_user_message(
        raw_rel, content, skill_rel=skill_rel, is_chunk=is_chunk
    )
    slug = _sanitize_slug(chunk_rel)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pending_path = PENDING_DIR / f"compress-{slug}-{ts}.json"
    out_rel = str(compression_output_path(chunk_rel).relative_to(WORKSPACE_PATH)).replace("\\", "/")

    payload = {
        "kind": "compression",
        "skill": skill_rel,
        "raw_path": raw_rel,
        "chunk_path": chunk_rel if is_chunk else None,
        "file_hash": file_hash,
        "output_file": out_rel,
        "output_language": source_lang,
        "user_message": user_message,
        "created_at": datetime.now().isoformat(),
    }
    pending_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return [pending_path]


def prepare_for_file(rel_path: str, abs_path: Path, file_hash: str) -> list[Path]:
    """Single-unit pending (legacy callers)."""
    content = abs_path.read_text(encoding="utf-8", errors="replace")
    return prepare_for_unit(
        raw_rel=rel_path,
        chunk_rel=rel_path,
        content=content,
        file_hash=file_hash,
        is_chunk=False,
    )
