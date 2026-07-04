"""Fix malformed nested (Source: [[...]]) wikilinks in wiki pages."""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

from config import WIKI_DIR, WORKSPACE_PATH

logger = logging.getLogger(__name__)

# [[(Source: [[inner/path.md]]) → [[raw/path.md]]  or  [[(Source: [[path]]) — note]]
MALFORMED_SOURCE = re.compile(
    r"\[\[\(Source:\s*\[\[([^\]]+)\]\]\)"
    r"(?:\s*→\s*\[\[([^\]]+)\]\])?"
    r"(?:\s*—\s*([^\]\n]+))?"
    r"\]*"
)


def fix_line(line: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        raw = (match.group(2) or "").strip()
        note = (match.group(3) or "").strip()
        if not inner.startswith(("raw/", "compression/", "discovery/", "self-wiki/")):
            if inner.startswith("_posts/") or inner.startswith("origin-"):
                inner = f"raw/{inner}"
            elif not inner.startswith("../"):
                inner = f"compression/{inner}"
        if raw and not raw.startswith("raw/"):
            if raw.startswith("_posts/") or raw.startswith("origin-"):
                raw = f"raw/{raw}"
        if raw:
            return f"[[{inner}]] → [[{raw}]]"
        if note:
            return f"[[{inner}]] — {note}"
        return f"[[{inner}]]"

    if "[[(Source:" not in line:
        return line
    prefix = "- " if line.lstrip().startswith("-") else ""
    body = line.lstrip()[2:] if prefix else line
    fixed = MALFORMED_SOURCE.sub(_replace, body)
    return f"{prefix}{fixed}" if prefix else fixed


def fix_content(text: str) -> tuple[str, int]:
    changes = 0
    lines: list[str] = []
    for line in text.splitlines():
        new_line = fix_line(line)
        if new_line != line:
            changes += 1
        lines.append(new_line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), changes


def fix_wiki(*, dry_run: bool = False) -> dict:
    wiki_files = [
        f
        for f in WIKI_DIR.rglob("*.md", recurse_symlinks=True)
        if f.name not in ("INDEX.md", "audit.md") and "-Hub" not in f.name
    ]
    total_changes = 0
    touched: list[str] = []
    for path in sorted(wiki_files):
        original = path.read_text(encoding="utf-8")
        fixed, n = fix_content(original)
        if n:
            total_changes += n
            rel = str(path.relative_to(WORKSPACE_PATH))
            touched.append(rel)
            if not dry_run:
                path.write_text(fixed, encoding="utf-8")
                logger.info("Fixed %d line(s) in %s", n, rel)
    return {"files_touched": len(touched), "lines_fixed": total_changes, "paths": touched}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix malformed provenance wikilinks in wiki/")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = fix_wiki(dry_run=args.dry_run)
    logger.info(
        "Done: %d file(s), %d line(s) %s",
        result["files_touched"],
        result["lines_fixed"],
        "(dry-run)" if args.dry_run else "fixed",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
