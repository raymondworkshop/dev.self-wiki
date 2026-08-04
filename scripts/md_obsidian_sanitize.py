"""Normalize LLM markdown for Obsidian: replace common LaTeX with Unicode."""

from __future__ import annotations

import re
from pathlib import Path

# Inline math symbols LLMs emit that Obsidian often shows literally.
_LATEX_INLINE = {
    r"\rightarrow": "→",
    r"\to": "→",
    r"\Rightarrow": "⇒",
    r"\leftarrow": "←",
    r"\Leftarrow": "⇐",
    r"\leftrightarrow": "↔",
    r"\Leftrightarrow": "⇔",
    r"\neq": "≠",
    r"\ne": "≠",
    r"\approx": "≈",
    r"\times": "×",
    r"\cdot": "·",
    r"\pm": "±",
    r"\leq": "≤",
    r"\geq": "≥",
    r"\infty": "∞",
    r"\Delta": "Δ",
    r"\delta": "δ",
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
}

_DOLLAR_CMD = re.compile(
    r"\$\\("
    + "|".join(re.escape(k[1:]) for k in _LATEX_INLINE)
    + r")\$"
)


def sanitize_obsidian_markdown(text: str) -> str:
    """Replace `$\\command$` with Unicode so Obsidian renders without MathJax."""

    if not text or "$\\" not in text:
        return text

    def _repl(m: re.Match[str]) -> str:
        cmd = "\\" + m.group(1)
        return _LATEX_INLINE.get(cmd, m.group(0))

    return _DOLLAR_CMD.sub(_repl, text)


def sanitize_markdown_file(path: Path) -> bool:
    """Rewrite file if sanitization changes content. Returns True if written."""

    original = path.read_text(encoding="utf-8")
    cleaned = sanitize_obsidian_markdown(original)
    if cleaned == original:
        return False
    path.write_text(cleaned, encoding="utf-8")
    return True


def sanitize_tree(roots: list[Path], *, glob: str = "**/*.md") -> list[Path]:
    """Sanitize all matching markdown files under roots. Returns changed paths."""

    changed: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            paths = [root]
        else:
            paths = sorted(root.glob(glob))
        for path in paths:
            if path.is_file() and sanitize_markdown_file(path):
                changed.append(path)
    return changed


def main() -> int:
    import argparse

    from config import VAULT_DIR, WORKSPACE_PATH, workspace_relpath

    parser = argparse.ArgumentParser(
        description="Replace $\\rightarrow$ etc. with Unicode in vault markdown"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or dirs (default: discovery, gap, evolution, outputs)",
    )
    args = parser.parse_args()
    if args.paths:
        roots: list[Path] = []
        for p in args.paths:
            path = Path(p)
            if path.is_absolute():
                roots.append(path)
                continue
            for cand in (WORKSPACE_PATH / path, VAULT_DIR / path, path):
                if cand.exists():
                    roots.append(cand)
                    break
            else:
                roots.append(WORKSPACE_PATH / path)
    else:
        roots = [
            VAULT_DIR / "discovery",
            VAULT_DIR / "gap",
            VAULT_DIR / "evolution",
            VAULT_DIR / "outputs",
        ]

    changed = sanitize_tree(roots)
    for path in changed:
        print(f"fixed {workspace_relpath(path)}")
    print(f"sanitized {len(changed)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
