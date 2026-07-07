# Operating Manual (LLM-Native)

> **Socratic Mirror** — LLM as OS, wiki as context window for self-reflection. High signal-to-noise: every word earns its place.

**Goal:** Self-discovery and deep cognitive engagement through iterative distillation.

## Who does what

| Mode | Does | Does not |
|------|------|----------|
| **Composer (default)** | `wiki-synthesize`, `discovery/`, `gap/`, `evolution/` via `skills/` | — |
| **Python** | `register-reference`, `ingest`, `audit` — deterministic | LLM |
| **Cloud API (optional)** | `make query`, `make audit LINT=1` (`LLM_PROVIDER=gemini`) | Primary path |
| **Local MLX** | Only with `ALLOW_LOCAL_LLM=1`; last resort via `LLM_MLX_LAST_RESORT=1` (default) | Primary |

`make wiki-synthesize` / `make sync` LLM batch: opt-in only (`ALLOW_PYTHON_LLM=1`). Prefer Composer for quality.

Pipeline detail: [design.md](design.md) · daily commands: [README.md](README.md)

---

## Knowledge hierarchy

| Level | Path | Content |
|-------|------|---------|
| L0 Raw | `raw/` | Unprocessed notes, logs, clippings — read-only |
| L1 | `wiki/` | Themes, patterns (`type/synthesis`) |
| L2 | `wiki/` | Principles, mental models (`type/principle`) |

Also: `discovery/`, `gap/`, `evolution/` (agent reports) · `outputs/` (query) · `log/` (index, pending, `sources.json`) · `twin/PROFILE.md` (after ingest, under `self-wiki/`) · `INDEX.md` (Obsidian hub).

`raw/` folders: `_posts/`, `origin-apple-notes/`, `twitter/`. Twitter → `register-reference` only (`sources.json` = external, not beliefs).

Long raw files are chunked in-memory for wiki-synthesize (see `scripts/raw_chunking.py`).

---

## Workflows

### Ingest (Composer — default)

1. [wiki-synthesize](skills/wiki-synthesize.md) on changed raw → update 1–3 wiki pages
2. `make ingest`

End every wiki update with provenance (always `raw/` prefix):

```markdown
- (Source: [[raw/_posts/learning/foo.md]])
```

Match source language (Chinese ↔ Chinese, English ↔ English). Progress: `make progress`.

**Batch:** `make sync` (changed raw → wiki-synthesize → ingest).

### Agents & reflect

| Command | What it does | Output |
|---------|--------------|--------|
| `make discover` | Hidden cross-corpus patterns | `self-wiki/discovery/{date}.md` |
| `make gap` | Knowledge gaps + reading list (needs discovery) | `self-wiki/gap/{date}.md` |
| `make evolution` | Knowledge-state snapshot | `self-wiki/evolution/{date}.md` |
| `make agents` | All three reports in order | above |
| `make reflect` | `agents` + `ingest` + `audit LINT=1` | weekly review |

Skills: [discovery.md](skills/discovery.md) · [gap.md](skills/gap.md) · [evolution.md](skills/evolution.md). Run `discover` before `gap`.

### wiki-synthesize thresholds

| Case | Rule |
|------|------|
| New L1 (single source) | confidence ≥ 0.80 |
| Cross-file incubation | `support_count ≥ 3`, `mean_conf ≥ 0.78`, `max_conf ≥ 0.82` → `make incubate-themes` |
| Skip | `raw/twitter/**` (reference only) |

Backfill: `make wiki-synthesize WAVE=theme_links LIMIT=50 INGEST=1`

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
- **Inferred patterns:** tag `[AI Synthesis]` or `[Socratic Observation]`
- **`## Backlinks`** (auto via ingest): Evolved from · Mentioned in · Contradicts (Cognitive Shift)

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
3. **Language fidelity** — no EN↔中文 translation unless asked (`raw/`, `wiki/`, `outputs/`, reports)
4. **Socratic proactivity** — flag blind spots and contradictions as Cognitive Shift
5. **Context efficiency** — concise pages; split when long
6. **Traceability** — no invented principles; L2 needs L0/L1 evidence
