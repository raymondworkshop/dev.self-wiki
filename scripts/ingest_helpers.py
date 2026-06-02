"""Shared ingest helpers (deterministic)."""

from __future__ import annotations

import re

from llm_provider import provider_name


def detect_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "Chinese"
    return "English"


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
    """Return threshold, chunk_size, overlap for a provider."""
    if provider_name(provider) == "gemini":
        return 8000, 10000, 500
    return 220, 500, 50
