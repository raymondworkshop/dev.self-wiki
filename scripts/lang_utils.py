"""Source language detection for ingest skills."""

from __future__ import annotations

import re


def detect_language(text: str) -> str:
    """Return 'Chinese' or 'English' from predominant script in source text."""

    if not text or not text.strip():
        return "English"

    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))

    if cjk == 0:
        return "English"
    if latin == 0:
        return "Chinese"
    return "Chinese" if cjk >= latin else "English"


def epistemic_label_instruction() -> str:
    return (
        "## EPISTEMIC LABELS\n"
        "Grounded paraphrase from the source needs **no tag** — write plainly.\n"
        "Prefix **only** when you go beyond the source:\n"
        "- **[AI Synthesis]** — pattern, implication, or connection not explicit in source.\n"
        "- **[Socratic Observation]** — reflective challenge or blind-spot prompt; not a source fact.\n"
        "Rules:\n"
        "- Blockquote `>` and `## Key points` bullets: default untagged faithful summary.\n"
        "- Use **[AI Synthesis]** sparingly — one line in the summary or a few bullets at most.\n"
        "- Fragment / word-list sources: list items plainly; at most one **[AI Synthesis]** line "
        "on what the list appears to be. Do NOT invent a narrative.\n"
        "- Never present **[AI Synthesis]** as if it were the author's stated belief.\n"
    )


def language_output_instruction(lang: str) -> str:
    """Mandatory LLM instruction block for ingest skills."""

    other = "English" if lang == "Chinese" else "Chinese"
    return (
        f"## LANGUAGE (mandatory)\n"
        f"Output language: **{lang}**\n"
        f"- Write ALL of: YAML `title`, `description`, blockquote summary, section headers, "
        f"and body prose in **{lang}**.\n"
        f"- Do NOT translate into {other}. Do NOT default to {other}.\n"
        f"- If the source mixes languages, mirror the source's predominant language ({lang}); "
        f"keep quoted phrases in their original wording.\n"
    )
