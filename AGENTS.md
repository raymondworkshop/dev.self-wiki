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
# My Self-Wiki Operating Manual (LLM-Native Edition)

## Operating Philosophy: The Socratic Mirror

This wiki is a **Reasoning Engine** and a **Socratic Mirror**. We treat LLMs as the "OS" and the wiki as the "Context Window" for high-resolution self-reflection.

- **Dual-Model Workflow**:
  - **Gemini (Strategic)**: Performs high-level architectural design, system auditing, and knowledge synthesis strategy.
  - **Local MLX (Operational)**: Executes routine data processing, file synchronization (`make sync`), and continuous synthesis based on Gemini’s architectural definitions.

- **Goal**: Foster self-discovery, emotional regulation, and deep cognitive engagement through iterative distillation.
- **Principle**: High signal-to-noise ratio. Every word must earn its place in the context window.

## Knowledge Hierarchy (The Distillation Loop)
1. **Raw (Level 0)**: Unprocessed thoughts, logs, diary entries, and external clippings. (High Entropy/Volume)
2. **Synthesis (Level 1)**: Integrated themes and patterns, and the process of logical deduction derived from multiple raw sources. (Pattern Recognition)
3. **Principle/Mental Model (Level 2)**: Compressed, actionable "source code" for my life. (High Utility/Low Volume)

## Structure Rules
- `self-wiki/raw/`: Input stream. Read-only for AI. Never modify raw files.
- `self-wiki/wiki/`: The "Second Brain". AI-curated, structured, and cross-linked.
- `self-wiki/outputs/`: Snapshots of reasoning, reports, and deep-dives.
- `self-wiki/log/pending/`: Harness builds JSON here; skills read `user_message` from pending files.
- `self-wiki/log/INDEX.json` + `log/index.md`: Machine index (auto); `self-wiki/INDEX.md`: human Obsidian hub.
- `twin/PROFILE.md`: Digital twin snapshot (post-ingest).


## Agent Skills (Operational Mandates)

### `sync-wiki` (`make sync`)
- **Action**: Ingest `raw/`, identify patterns, update/create `wiki/` entries.
- **Note**: Focus on *lossy compression*—discard the fluff, capture the core insight.

### `audit-wiki` (`make audit` / `make audit LINT=1`)
- **`make audit`**: Deterministic scan — structure, red links, duplicate themes, Level-2 guidance.
- **`make audit LINT=1`**: Above + one global LLM pass via `skills/lint.md` for cross-page cognitive contradictions.
- **Socratic Duty**: Prompt the user when a new insight contradicts an old principle or habit.

### `query-wiki` (`make query`)
- **Pipeline**: `prepare-query` (deterministic retrieval) → `run-skill(query.md)` → save output.
- **Profiles**: [skills/query-profiles.yaml](skills/query-profiles.yaml) — values, personality_logic, swot, general.
- **Output**: Synthesis + Provenance (tracing back to raw sources).

## Wiki Standards (LLM-Optimized)
- **One Topic Per File**: Keep files focused and modular.
- **YAML Front Matter**: Must include `last_updated` (ISO 8601), `title`, `description`, `level` (0-2), and `tags`.
- **Socratic Summary**: Every file starts with a 2-3 sentence blockquote `>` that captures the "essence" for the LLM's quick context.
- **Traceability**: Every claim must link to its origin `(Source: [[raw-file-path]])`.
- **Evolution Section**: A `## Evolution` section tracking how this specific idea or belief has changed over time.
- **Backlinks**: Automated section for:
  ```markdown
  ## Backlinks
  - **Evolved from**: [[Topic]]
  - **Mentioned in**: [[Topic]]
  - **Contradicts**: [[Topic]] (Cognitive Shift)
  ```

## Taxonomy (Functional Tags)
- `type/source`: The raw material.
- `type/synthesis`: Connecting the dots across entries.
- `type/principle`: Fundamental laws of my own operating system.
- `type/shift`: Documentation of a significant change in belief or behavior.

## Interaction Protocols (Output Formats)
- **Deep Analysis**: Subject → Analysis Framework → Key Insights → Implications → Socratic Question.
- **Comparison**: Entity A vs Entity B → Overlap → Divergence → Synthesis/Conclusion.
- **Recommendation**: Context → Options (Max 3) → Rationale → Potential Pitfalls.

## Core Mandates
1. **Fidelity to Raw Truth**: The AI must never "hallucinate" a belief, preference, or event. Every claim in the `wiki/` with confidence must be a direct distillation of `raw/` evidence.
2. **Explicit Interpretation**: When the AI identifies a pattern that isn't explicitly stated (e.g., an underlying anxiety), it must label it as `[AI Synthesis]` or `[Socratic Observation]` to distinguish it from "raw truth".
3. **Language Fidelity**: Match the input language perfectly. Do not translate between English/Chinese unless asked.
4. **Socratic Proactivity**: If a new note reveals a blind spot, bias, or contradiction, flag it as a "Cognitive Shift".
5. **Context Efficiency**: Keep wiki files concise. If a file gets too long, refactor into sub-topics.
6. **Traceability**: Never "hallucinate" a principle; every Level 2 insight must be grounded in Level 0/1 evidence. Use blockquotes for direct evidence.
