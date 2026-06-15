"""Prepare discovery evidence pack (deterministic, no LLM)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config import COMPRESSION_DIR, PENDING_DIR, WIKI_DIR, WORKSPACE_PATH
from llm_provider import provider_name


def _sample_from_dir(directory: Path, limit: int) -> list[dict]:
    if not directory.exists() or limit <= 0:
        return []
    files = sorted(directory.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    samples: list[dict] = []
    for path in files[:limit]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(WORKSPACE_PATH)).replace("\\", "/")
        samples.append({"path": rel, "excerpt": text[:2000]})
    return samples


def _stratified_compression_samples(*, total_limit: int = 50) -> list[dict]:
    """Sample across lanes — avoid twitter-only packs when those files are newest."""

    strata: list[tuple[str, int]] = [
        ("_posts/learning", 12),
        ("_posts/diary", 8),
        ("_posts/self", 8),
        ("_posts/notes", 6),
        ("_posts/philosophy", 4),
        ("_posts/research", 4),
        ("origin-apple-notes", 10),
        ("twitter", 8),
    ]
    seen: set[str] = set()
    out: list[dict] = []
    for rel_dir, cap in strata:
        base = COMPRESSION_DIR / rel_dir
        for item in _sample_from_dir(base, cap):
            if item["path"] in seen:
                continue
            seen.add(item["path"])
            out.append(item)
            if len(out) >= total_limit:
                return out
    return out


def _sample_files(directory: Path, limit: int = 40) -> list[dict]:
    return _sample_from_dir(directory, limit)


def write_pending(*, provider: str | None = None) -> Path:
    compression_samples = _stratified_compression_samples(total_limit=50)
    wiki_samples = _sample_files(WIKI_DIR, limit=20)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pending_path = PENDING_DIR / f"discover-{ts}.json"
    user_message = (
        f"Discovery run {datetime.now().date().isoformat()}\n"
        f"Provider hint: {provider_name(provider)}\n\n"
        "## Compression samples\n"
        + "\n\n".join(f"### {s['path']}\n{s['excerpt']}" for s in compression_samples)
        + "\n\n## Wiki samples\n"
        + "\n\n".join(f"### {s['path']}\n{s['excerpt']}" for s in wiki_samples)
    )
    out_name = f"self-wiki/discovery/{datetime.now().date().isoformat()}.md"
    payload = {
        "kind": "discovery",
        "skill": "skills/discovery.md",
        "user_message": user_message,
        "output_file": out_name,
        "created_at": datetime.now().isoformat(),
    }
    pending_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return pending_path
