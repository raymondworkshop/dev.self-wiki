# Operating Manual (LLM-Native)

> **Socratic Mirror** — LLM as OS, wiki as context window for self-reflection. High signal-to-noise: every word earns its place.

**Goal:** Self-discovery and deep cognitive engagement through iterative distillation.

## Who does what

| Mode | Does | Does not |
|------|------|----------|
| **Composer (default)** | Digest → `compression/`, `discovery/`, `gap/`, `evolution/` via `skills/` | — |
| **Python** | `register-reference`, `post-ingest`, `audit` — deterministic | LLM |
| **Cloud API (optional)** | `make query`, `make audit LINT=1` (`QUERY_LLM_PROVIDER=gemini`) | Primary path |
| **Local MLX** | Only with `ALLOW_LOCAL_LLM=1`; last resort via `LLM_MLX_LAST_RESORT=1` (default) | Primary |

`make compress` / `make sync` LLM batch: opt-in only (`ALLOW_PYTHON_LLM=1`). Prefer Composer for quality.

Pipeline detail: [design.md](design.md) · daily commands: [README.md](README.md)

---

## Knowledge hierarchy

| Level | Path | Content |
|-------|------|---------|
| L0 Raw | `raw/` | Unprocessed notes, logs, clippings — read-only |
| L0.5 | `compression/` | Lossy digests (≤~80 lines); path mirrors `raw/` |
| L1 | `wiki/` | Themes, patterns (`type/synthesis`) |
| L2 | `wiki/` | Principles, mental models (`type/principle`) |

Also: `discovery/`, `gap/`, `evolution/` (agent reports) · `outputs/` (query) · `log/` (index, pending, `sources.json`) · `twin/PROFILE.md` (post-ingest) · `INDEX.md` (Obsidian hub).

`raw/` folders: `_posts/`, `origin-apple-notes/`, `twitter/`. Twitter → `register-reference` only (`sources.json` = external, not beliefs).

**Never:** raw → `wiki/` in one step.

---

## Workflows

### Ingest (Composer — default)

1. Digest changed raw → `compression/` ([ingest-summary](skills/ingest-summary.md) / [ingest-thoughts](skills/ingest-thoughts.md))
2. [wiki-synthesize](skills/wiki-synthesize.md) → update 1–3 wiki pages
3. `make post-ingest`

End every digest with provenance (always `raw/` prefix):

```markdown
- (Source: [[raw/_posts/learning/foo.md]])
```

Match source language (Chinese ↔ Chinese, English ↔ English). Progress: `make progress`.

**Batch:** `make sync` (changed raw → compression → wiki → post-ingest). Optional `POSTS_BATCH=1` for small `_posts`.

### wiki-synthesize thresholds

| Case | Rule |
|------|------|
| New L1 (single digest) | confidence ≥ 0.80 |
| Cross-file incubation | `support_count ≥ 3`, `mean_conf ≥ 0.78`, `max_conf ≥ 0.82` → `make incubate-themes` |
| Skip | `compression/twitter/**` |

Backfill: `make wiki-synthesize WAVE=theme_links LIMIT=50 POST_INGEST=1`

### Audit · Query · Promote

| Command | Behavior |
|---------|----------|
| `make audit` | Structure, red links, duplicate themes, L2 guidance |
| `make audit LINT=1` | Above + `skills/lint.md` — cross-page contradictions. **Flag Cognitive Shift** when new insight contradicts old principle |
| `make query` | retrieve → `query.md` → save with provenance ([query-profiles.yaml](skills/query-profiles.yaml)) |
| `make promote … CONFIRM=1` | When answer has `[Cognitive Shift]` or user confirms; merges under `### Promoted from query`. Target: existing L1 — not ad-hoc L2 from one query |

---

## Wiki page standards

- **One topic per file** — refactor if too long
- **Front matter:** `last_updated`, `title`, `description`, `level` (0–2), `tags`
- **Opening:** 2–3 sentence blockquote `>` (essence for LLM)
- **`## Evolution`** — how this belief changed over time
- **Traceability:** every claim → `(Source: [[raw/…]])`; L2 grounded in L0/L1; blockquotes for direct evidence
- **Inferred patterns:** tag `[AI Synthesis]` or `[Socratic Observation]` (not needed for grounded paraphrase in `compression/`)
- **`## Backlinks`** (auto via post-ingest): Evolved from · Mentioned in · Contradicts (Cognitive Shift)

**Tags:** `type/source` · `type/synthesis` · `type/principle` · `type/shift`

---

## Output formats

- **Deep analysis:** Subject → Framework → Insights → Implications → Socratic question
- **Comparison:** A vs B → Overlap → Divergence → Synthesis
- **Recommendation:** Context → Options (max 3) → Rationale → Pitfalls

---

## Core mandates

1. **No hallucinated beliefs** — wiki claims must distill `raw/` evidence
2. **Label inference** — `[AI Synthesis]` / `[Socratic Observation]` when not explicit in source
3. **Language fidelity** — no EN↔中文 translation unless asked (`compression/`, `wiki/`, `outputs/`, reports)
4. **Socratic proactivity** — flag blind spots and contradictions as Cognitive Shift
5. **Context efficiency** — concise pages; split when long
6. **Traceability** — no invented principles; L2 needs L0/L1 evidence
