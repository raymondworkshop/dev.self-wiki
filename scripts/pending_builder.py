"""
Shared helpers for writing "pending" JSON envelopes.

This keeps prepare_* modules small: they only build user_message and domain fields,
while the common JSON envelope + write logic lives here.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_skill_pending_json(
    *,
    pending_dir: Path,
    pending_name: str,
    kind: str,
    skill: str,
    user_message: str,
    output_file: str,
    extra: dict | None = None,
    created_at: str | None = None,
) -> Path:
    """
    Write a pending JSON file.

    - `skill` is the resolved skill path stored in the pending file.
    - `output_file` is the output file path stored in the pending file.
    """

    payload: dict = {
        "kind": kind,
        "skill": skill,
        "user_message": user_message,
        "output_file": output_file,
    }
    if created_at is not None:
        payload["created_at"] = created_at
    if extra:
        payload.update(extra)

    pending_dir.mkdir(parents=True, exist_ok=True)
    pending_path = pending_dir / pending_name
    pending_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return pending_path

