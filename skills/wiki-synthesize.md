---
name: wiki-synthesize
description: Link one raw source into existing wiki pages (L1 updates only).
inputs: raw path, source text, wiki themes, matched page excerpts, max_theme_updates
outputs: JSON object with actions[] for apply-ingest
---

# Wiki Synthesize Skill

You integrate **one raw source note** into the existing personal wiki — append evidence to theme pages, flag tension, create L1 only when necessary.

## Operating rules

1. **Ground in source only** — do not invent content beyond the raw file (or chunk).
2. **Max updates** — respect `max_theme_updates` from the user message; never exceed it.
3. **Prefer existing pages** — update matched wiki themes before creating new titles.
4. **No L2 from one source** — do not set `level: 2` or tag `type/principle` unless the user message explicitly says cross-source L2 promotion is allowed.
5. **New L1 (single source)** — only when the note states an explicit belief-level pattern AND no existing title matches (**confidence ≥ 0.80**).
6. **New L1 (cross-file incubation)** — when the same candidate theme appears across files with:
   - `support_count ≥ 3`
   - `mean_conf ≥ 0.78`
   - `max_conf ≥ 0.82`
   - each supporting file `confidence ≥ 0.75`
   Use `make incubate-themes` (deterministic cluster pass) or Composer with the same thresholds.
7. **Contradictions** — if the source challenges an existing wiki claim, use tag `type/shift` and prefix body with `[Cognitive Shift]`; do not replace old content.
8. **Language** — match the source language (Chinese or English).
9. **Provenance** — `new_body_content` must cite `(Source: [[raw/...]])` from the user message.
10. **Epistemic labels** — prefix inferred lines with `[AI Synthesis]`; reflective challenges with `[Socratic Observation]`.
11. **Never downgrade** — do not reduce an existing page `level` or remove `type/principle` on merge.

## Confidence scoring

- 0.9–1.0 (Literal): Direct statement in source.
- 0.7–0.89 (Explicit Pattern): Strong pattern from source bullets.
- 0.5–0.69 (Synthesized): Prefix body with `[AI Synthesis]`.
- Below 0.5: omit the action.

## Output format

Respond with **only** a JSON object (no markdown fences):

```json
{
  "raw_path": "raw/origin-apple-notes/example.md",
  "actions": [
    {
      "target_title": "Exact existing wiki title",
      "confidence_score": 0.88,
      "confidence_rationale": "Brief evidence from source",
      "level": 1,
      "summary": "2-3 sentence Socratic summary for the nugget",
      "description": "One-line essence",
      "new_body_content": "Distilled nugget with (Source: [[raw/...]])",
      "tags": ["type/synthesis", "topic/..."]
    }
  ]
}
```

If nothing applies, return `{"raw_path": "...", "actions": []}`.
