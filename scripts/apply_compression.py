"""Write compression markdown from LLM output or pending JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path

from compression_provenance import fix_provenance
from config import WORKSPACE_PATH
from prepare_compress import compression_output_path


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:markdown|md)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def apply_compression_text(text: str, *, rel_path: str, out_rel: str | None = None) -> Path:
    body = _strip_fences(text)
    body = fix_provenance(body, rel_path)
    if out_rel:
        out_path = WORKSPACE_PATH / out_rel
    else:
        out_path = compression_output_path(rel_path)
        if not out_path.is_absolute():
            out_path = WORKSPACE_PATH / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return out_path


def apply_from_pending_output(pending_path: Path, response_text: str) -> Path:
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    rel = pending.get("raw_path", "")
    if not rel:
        raise ValueError(f"pending missing raw_path: {pending_path}")
    return apply_compression_text(response_text, rel_path=rel)


def apply_from_file(actions_path: Path) -> Path:
    data = json.loads(actions_path.read_text(encoding="utf-8"))
    text = data.get("compression_markdown") or data.get("text", "")
    rel = data.get("raw_path", "")
    if not text or not rel:
        raise ValueError(f"Invalid compression actions: {actions_path}")
    return apply_compression_text(text, rel_path=rel)


def apply_batch_digests(data: dict) -> list[Path]:
    """Write one compression file per digest in batch JSON."""

    paths: list[Path] = []
    for digest in data.get("digests", []):
        raw_path = digest.get("raw_path", "")
        body = digest.get("body") or digest.get("compression_markdown") or ""
        if not raw_path or not body:
            continue
        if not raw_path.startswith("raw/"):
            raw_path = f"raw/{raw_path.lstrip('/')}"
        paths.append(apply_compression_text(body, rel_path=raw_path))
    if not paths:
        raise ValueError("Batch response missing digests[] with raw_path + body")
    return paths
