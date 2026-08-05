"""Operational log (deterministic): newest entries first."""

from __future__ import annotations

import re
from datetime import datetime

from config import LOG_DIR, LOG_MD

LOG_ENTRY_RE = re.compile(r"^## \[[^\]]+\] .+$", re.MULTILINE)

HEADER = (
    "# Self-Wiki Log\n\n"
    "Operational record (ingest, sync, query, rdatabase, promote, agents, …). "
    "Newest entries first. Prefer verbs: created / updated / deleted / ran.\n\n"
)


def short_text(text: str, max_len: int = 72) -> str:
    s = (text or "").replace("\n", " ").strip()
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def _split_header_entries(text: str) -> tuple[str, list[str]]:
    matches = list(LOG_ENTRY_RE.finditer(text))
    if not matches:
        header = text.rstrip() + ("\n\n" if text.strip() else "")
        return header, []
    header = text[: matches[0].start()]
    if not header.strip():
        header = HEADER
    elif not header.endswith("\n\n"):
        header = header.rstrip() + "\n\n"
    entries = [m.group(0).rstrip() for m in matches]
    return header, entries


def append_log(kind: str, summary: str) -> None:
    """Prepend a log entry (newest first). Dedupes if identical to current top entry."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    line = f"## [{stamp}] {kind} | {summary}"

    if LOG_MD.exists():
        existing = LOG_MD.read_text(encoding="utf-8")
        header, entries = _split_header_entries(existing)
        if entries and entries[0] == line:
            return
        body = "\n".join([line, *entries]) + "\n"
        LOG_MD.write_text(header + body, encoding="utf-8")
    else:
        LOG_MD.write_text(HEADER + line + "\n", encoding="utf-8")


def rewrite_newest_first() -> int:
    """One-shot: reverse chronological ## entries so newest is first. Returns entry count."""
    if not LOG_MD.exists():
        return 0
    text = LOG_MD.read_text(encoding="utf-8")
    header, entries = _split_header_entries(text)
    if len(entries) <= 1:
        return len(entries)
    entries = list(reversed(entries))
    if "Newest entries first" not in header:
        header = HEADER
    LOG_MD.write_text(header + "\n".join(entries) + "\n", encoding="utf-8")
    return len(entries)
