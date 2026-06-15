"""Normalize compression provenance links to raw/... paths."""

from __future__ import annotations

import re


def normalize_raw_link(rel_path: str) -> str:
    rel = rel_path.replace("\\", "/").strip().lstrip("/")
    if rel.startswith("self-wiki/raw/"):
        rel = rel[len("self-wiki/raw/") :]
    if rel.startswith("raw/"):
        return rel
    return f"raw/{rel}"


def canonical_source_line(raw_link: str) -> str:
    return f"(Source: [[{raw_link}]])"


def fix_provenance(body: str, rel_path: str) -> str:
    """Ensure Sources use (Source: [[raw/origin-apple-notes/foo.md]])."""

    raw_link = normalize_raw_link(rel_path)
    short = raw_link[len("raw/") :] if raw_link.startswith("raw/") else rel_path

    # Wikilink variants missing raw/
    for variant in {short, rel_path.lstrip("raw/"), rel_path}:
        if variant:
            body = body.replace(f"[[{variant}]]", f"[[{raw_link}]]")

    source_line = canonical_source_line(raw_link)

    # Normalize Chinese section headers to canonical form
    body = body.replace("## 来源", "## Sources").replace("## 关键点", "## Key points")

    if re.search(r"\(Source:\s*\[\[", body, re.IGNORECASE):
        body = re.sub(
            r"\(Source:\s*\[\[[^\]]+\]\]\)",
            source_line,
            body,
            flags=re.IGNORECASE,
        )
    elif "## Sources" in body or "## 来源" in body:
        if "## 来源" in body and "## Sources" not in body:
            body = body.replace("## 来源", "## Sources")
        body = re.sub(
            r"(## Sources\s*\n)([\s\S]*?)(\n## |\Z)",
            lambda m: (
                f"{m.group(1)}- {source_line}\n{m.group(3)}"
                if source_line not in m.group(2)
                else m.group(0)
            ),
            body,
            count=1,
        )
    else:
        body = body.rstrip() + f"\n\n## Sources\n\n- {source_line}\n"

    return body
