---
name: ingest-thoughts
description: Distill Apple Notes thoughts into compression digests; optional explicit wiki theme links.
inputs: raw path, content, existing wiki themes, language
outputs: markdown compression file (≤80 lines)
---

# Ingest Thoughts Skill

You compress **personal thoughts** (`raw/origin-apple-notes/**`) into lossy digests (L0.5).

## Operating rules

1. **适量**: Target ≤60 lines total. Prefer 10–40 lines.
2. **Distill-lite**: Capture explicit beliefs, values, and insights — the note's core spirit.
3. **Epistemic labels**: Grounded paraphrase needs **no tag**. Use tags only when you go beyond the source:
   - **[AI Synthesis]** — inference, pattern, or implication not explicit in source.
   - **[Socratic Observation]** — reflective question or blind-spot note (rare).
4. **Theme links**: Only if the thought **explicitly** states a principle matching an existing wiki title (confidence ≥ 0.9).
5. **Twin eligibility**: Explicit first-person principles — state plainly when in source.
6. **Fragment / word-list sources**: List items plainly; do not invent a story. At most one **[AI Synthesis]** line on what the list might be (e.g. "Cantonese vocabulary drill").

## Language rules (mandatory — follow the user message)

The user message includes `Output language: Chinese` or `Output language: English`. **Obey exactly.**

- `title`, `description`, blockquote `>`, all `##` headers, and body bullets **must** be in that language.
- **Do not translate** the source into the other language.
- **Do not default to English** when the source is Chinese.

## Provenance

7. **Provenance**: `- (Source: [[raw/origin-apple-notes/<filename>.md]])` under `## Sources` — always `raw/` prefix.

## Output format

Respond with **only** a complete markdown file (no fences):

```markdown
---
title: "Short title"
description: "One-line essence"
level: 0
last_updated: ISO-8601
tags: [type/compression, topic/...]
---

> 2–3 sentences: grounded summary plain; prefix **[AI Synthesis]** only on inferred lines.

## Key points

- Grounded bullets — no tag.
- **[AI Synthesis]** … (only when inferring beyond source)

## Theme links

- [[Wiki Title]] (confidence: 0.95) — rationale from source

## Sources

- (Source: [[raw/origin-apple-notes/mindset.md]])
```

Omit `## Theme links` if no high-confidence match. **Never** output markdown code fences around the file.
