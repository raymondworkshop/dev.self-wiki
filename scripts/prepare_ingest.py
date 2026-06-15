"""Build pending ingest packages (deterministic, zero LLM)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from config import INGEST_SKILL, PENDING_DIR, WORKSPACE_PATH
from llm_provider import provider_name
from wiki_themes import load_existing_themes


from lang_utils import detect_language


def chunk_text(text: str, max_lines: int = 500, overlap: int = 50):
    lines = text.splitlines()
    if not lines:
        return

    start = 0
    while start < len(lines):
        end = start + max_lines
        yield "\n".join(lines[start:end])
        if end >= len(lines):
            break
        start += max_lines - overlap


def chunk_params(provider: str | None = None) -> tuple[int, int, int]:
    if provider_name(provider) == "gemini":
        return 8000, 10000, 500
    return 220, 500, 50


def _sanitize_slug(rel_path: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", rel_path).strip("-")
    return slug[:80] or "source"


def build_ingest_user_message(
    rel_path: str,
    content: str,
    existing_themes: list[dict],
    *,
    is_chunk: bool = False,
) -> str:
    source_lang = detect_language(content)
    target_lang = "English" if source_lang == "Chinese" else "Chinese"
    chunk_note = " (This is a chunk of a larger file)" if is_chunk else ""

    titles_context = "\n".join(
        f"- {t['title']}" + (f" (alias: {t['alias']})" if t.get("alias") else "")
        for t in existing_themes
    )

    return f"""Execute the ingest-wiki skill for this raw source.

STRICT LANGUAGE RULE:
- Source language: {source_lang}
- All generated fields MUST be in {source_lang}
- For NEW titles, provide bilingual_alias in {target_lang}

Raw source: [[{rel_path}]]{chunk_note}

Content:
---
{content}
---

Existing Themes in the Wiki:
{titles_context}
"""


def build_pending_package(
    rel_path: str,
    content: str,
    file_hash: str,
    *,
    is_chunk: bool = False,
    chunk_index: int | None = None,
) -> dict:
    themes, _ = load_existing_themes()
    user_message = build_ingest_user_message(
        rel_path, content, themes, is_chunk=is_chunk
    )
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    slug = _sanitize_slug(rel_path)
    chunk_suffix = f"-chunk{chunk_index}" if chunk_index is not None else ""
    actions_name = f"ingest-actions-{stamp}-{slug}{chunk_suffix}.json"

    return {
        "kind": "ingest",
        "skill": str(INGEST_SKILL.relative_to(WORKSPACE_PATH)),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "raw_path": rel_path,
        "raw_hash": file_hash,
        "is_chunk": is_chunk,
        "chunk_index": chunk_index,
        "source_language": detect_language(content),
        "sources": [
            {
                "path": rel_path,
                "hash": file_hash,
                "language": detect_language(content),
            }
        ],
        "existing_themes": themes,
        "user_message": user_message,
        "actions_output": actions_name,
    }


def write_pending(pending: dict) -> Path:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    slug = _sanitize_slug(pending["raw_path"])
    chunk = pending.get("chunk_index")
    chunk_suffix = f"-chunk{chunk}" if chunk is not None else ""
    name = f"ingest-{stamp}-{slug}{chunk_suffix}.json"
    path = PENDING_DIR / name
    pending["pending_path"] = str(path.relative_to(WORKSPACE_PATH))
    path.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def prepare_for_file(rel_path: str, abs_path: Path, file_hash: str) -> list[Path]:
    content = abs_path.read_text(encoding="utf-8")
    line_count = len(content.splitlines())
    threshold, chunk_size, overlap = chunk_params(provider_name())

    pending_paths: list[Path] = []
    if line_count > threshold:
        for i, chunk in enumerate(chunk_text(content, chunk_size, overlap)):
            pending = build_pending_package(
                rel_path,
                chunk,
                file_hash,
                is_chunk=True,
                chunk_index=i + 1,
            )
            pending_paths.append(write_pending(pending))
    else:
        pending = build_pending_package(rel_path, content, file_hash)
        pending_paths.append(write_pending(pending))

    return pending_paths
