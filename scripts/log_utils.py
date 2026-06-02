"""Append-only operational log (deterministic)."""

from __future__ import annotations

from datetime import datetime

from config import LOG_DIR, LOG_MD


def append_log(kind: str, summary: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    line = f"## [{stamp}] {kind} | {summary}\n"
    if LOG_MD.exists():
        existing = LOG_MD.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            existing += "\n"
        LOG_MD.write_text(existing + line, encoding="utf-8")
    else:
        header = (
            "# Self-Wiki Log\n\n"
            "Chronological record of ingest, query, and lint operations.\n\n"
        )
        LOG_MD.write_text(header + line, encoding="utf-8")
