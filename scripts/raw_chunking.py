"""Split long raw files for wiki-synthesize (in-memory chunks only)."""

from __future__ import annotations

from pathlib import Path

from ingest_profiles import resolve_profile

MEGA_LINE_THRESHOLD = 3000
DEFAULT_CHUNK_LINES = 400


def chunk_line_limit(rel: str) -> int:
    profile = resolve_profile(rel)
    if profile:
        return int(profile.get("chunk_lines") or profile.get("posts_batch_max_lines") or DEFAULT_CHUNK_LINES)
    return DEFAULT_CHUNK_LINES


def needs_chunking(rel: str, line_count: int) -> bool:
    limit = chunk_line_limit(rel)
    if line_count > MEGA_LINE_THRESHOLD:
        return True
    if rel.startswith("_posts/") and line_count > limit:
        return True
    if rel.startswith("twitter/") and line_count > limit:
        return True
    return False


def iter_units(rel: str, abs_path: Path) -> list[tuple[str, str]]:
    """Return (unit_id, chunk_content) units. Single unit if small."""

    content = abs_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    if not needs_chunking(rel, len(lines)):
        return [(rel, content)]

    limit = chunk_line_limit(rel)
    raw_path = Path(rel)
    stem = raw_path.stem
    parent = raw_path.parent
    units: list[tuple[str, str]] = []

    for i in range(0, len(lines), limit):
        chunk_lines = lines[i : i + limit]
        part = f"part-{(i // limit) + 1:03d}"
        if str(parent) == ".":
            unit_id = f"{stem}/{part}"
        else:
            unit_id = f"{parent}/{stem}/{part}"
        header = f"<!-- chunk {(i // limit) + 1} of {raw_path.name} -->\n"
        units.append((unit_id, header + "\n".join(chunk_lines)))

    return units
