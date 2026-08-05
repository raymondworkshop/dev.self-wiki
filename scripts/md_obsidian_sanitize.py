"""Sanitize markdown written into Obsidian wiki pages."""

from __future__ import annotations

import argparse
from pathlib import Path


def _unwrap_single_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return text

    lines = stripped.splitlines()
    if len(lines) < 3:
        return text

    first = lines[0].strip().lower()
    last = lines[-1].strip()
    if last != "```":
        return text
    if first not in {"```", "```md", "```markdown"}:
        return text
    return "\n".join(lines[1:-1]).strip() + "\n"


def sanitize_obsidian_markdown(text: str) -> str:
    """Light cleanup for wiki/ body text before Obsidian write."""
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.replace("\ufeff", "").replace("\u200b", "")
    cleaned = _unwrap_single_markdown_fence(cleaned)
    return cleaned.strip() + "\n"


def sanitize_file(path: Path) -> bool:
    """Sanitize a wiki markdown file in place; return True if changed."""
    original = path.read_text(encoding="utf-8")
    sanitized = sanitize_obsidian_markdown(original)
    if sanitized == original:
        return False
    path.write_text(sanitized, encoding="utf-8")
    return True


def _iter_markdown_paths(raw_path: Path) -> list[Path]:
    if raw_path.is_file():
        return [raw_path]
    if raw_path.is_dir():
        return sorted(p for p in raw_path.rglob("*.md") if p.is_file())
    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sanitize Obsidian wiki markdown (wiki/ only by convention)."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Wiki markdown files or directories (default: self-wiki/wiki).",
    )
    args = parser.parse_args()

    targets = [Path(p) for p in args.paths] if args.paths else [Path("self-wiki/wiki")]
    changed = 0
    scanned = 0

    for target in targets:
        paths = _iter_markdown_paths(target)
        if not paths and not target.exists():
            print(f"skip (missing): {target}")
            continue
        for path in paths:
            scanned += 1
            try:
                if sanitize_file(path):
                    changed += 1
                    print(f"updated: {path}")
            except Exception as exc:  # pragma: no cover - defensive CLI path
                print(f"error: {path} ({exc})")
                return 1

    print(f"done: scanned {scanned}, changed {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
