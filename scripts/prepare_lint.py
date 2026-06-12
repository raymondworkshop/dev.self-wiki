"""Build pending JSON for global cognitive lint (deterministic context, one LLM call)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from config import AUDIT_MD, LINT_SKILL, PENDING_DIR, WIKI_DIR, WORKSPACE_PATH
from build_twin_profile import lint_principle_excerpts, lint_profile_summary


def _truncate(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n… [truncated]"


def collect_backlink_contradicts() -> list[str]:
    items: list[str] = []
    if not WIKI_DIR.exists():
        return items

    for path in WIKI_DIR.rglob("*.md"):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        m = re.search(
            r"## Backlinks\s*\n.*?-\s*\*\*Contradicts\*\*:\s*(.+?)(?:\n-|\n## |\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if not m:
            continue
        line = m.group(1).strip()
        if not line or "none" in line.lower():
            continue
        rel = path.relative_to(WORKSPACE_PATH)
        items.append(f"- [[{rel}]]: {line}")
    return items[:30]


def build_user_message() -> str:
    audit_summary = ""
    if AUDIT_MD.exists():
        audit_summary = _truncate(AUDIT_MD.read_text(encoding="utf-8"), limit=4000)

    excerpts = lint_principle_excerpts()
    contradicts = collect_backlink_contradicts()

    parts = [
        "Perform global cognitive lint on this personal wiki.",
        "",
        "## Digital Twin Profile (deterministic snapshot)",
        lint_profile_summary(),
        "",
        "## Deterministic audit report (recent run)",
        audit_summary or "_No audit.md yet — run `make audit` first._",
        "",
        "## Backlink-declared contradictions",
    ]
    if contradicts:
        parts.extend(contradicts)
    else:
        parts.append("_None found in Backlinks sections._")

    parts.extend(["", "## Principle / high-level page excerpts"])
    if excerpts:
        parts.extend(excerpts)
    else:
        parts.append("_No level-2 or principle pages sampled._")

    return "\n".join(parts)


def write_pending() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pending_name = f"lint-{stamp}.json"
    output_name = f"lint-output-{stamp}.md"

    pending = {
        "kind": "lint",
        "skill": str(LINT_SKILL.relative_to(WORKSPACE_PATH)),
        "user_message": build_user_message(),
        "output_file": str((PENDING_DIR / output_name).relative_to(WORKSPACE_PATH)),
    }
    path = PENDING_DIR / pending_name
    path.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def merge_lint_into_audit(lint_text: str) -> Path:
    marker = "### ⚖️ Cognitive Lint (Global)"
    placeholder = "### ⚖️ Cognitive Shifts & [Socratic Observations]"

    if AUDIT_MD.exists():
        content = AUDIT_MD.read_text(encoding="utf-8")
    else:
        content = "# Wiki Audit & Socratic Mirror Report\n"

    if placeholder in content:
        before, _, after = content.partition(placeholder)
        after_parts = after.split("\n### ", 1)
        tail = ""
        if len(after_parts) > 1:
            tail = "\n### " + after_parts[1]
        content = before.rstrip() + "\n\n" + lint_text.strip() + tail
    elif marker in content:
        before, _, after = content.partition(marker)
        after_parts = after.split("\n### ", 1)
        tail = ""
        if len(after_parts) > 1:
            tail = "\n### " + after_parts[1]
        content = before.rstrip() + "\n\n" + lint_text.strip() + tail
    else:
        content = content.rstrip() + "\n\n---\n\n" + lint_text.strip() + "\n"

    AUDIT_MD.write_text(content, encoding="utf-8")
    return AUDIT_MD
