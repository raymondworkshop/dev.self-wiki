# My Self-Wiki Operating Manual (LLM-Native Edition)

## Operating Philosophy: The Socratic Mirror

This wiki is a **Reasoning Engine** and a **Socratic Mirror**. We treat LLMs as the "OS" and the wiki as the "Context Window" for high-resolution self-reflection.

- **Composer-first workflow**:
  - **Cursor Composer (default)**: Writes `compression/`, `discovery/`, `gap/`, `evolution/` directly in the vault using skills under `skills/`.
  - **Python (trust layer only)**: `register-reference`, `post-ingest`, `audit` — deterministic, no LLM.
  - **Cloud API (optional)**: `make query` / `make audit LINT=1` via `QUERY_LLM_PROVIDER=gemini` — not local MLX as primary.
- **Local MLX**: Primary only with `ALLOW_LOCAL_LLM=1`. **Last resort** when cloud fails or is unconfigured: `LLM_MLX_LAST_RESORT=1` (default). Do not use `make compress` unless `ALLOW_PYTHON_LLM=1`.

- **Goal**: Foster self-discovery, emotional regulation, and deep cognitive engagement through iterative distillation.
- **Principle**: High signal-to-noise ratio. Every word must earn its place in the context window.

## Knowledge Hierarchy (The Distillation Loop)
1. **Raw (Level 0)**: Unprocessed thoughts, logs, diary entries, and external clippings. (High Entropy/Volume)
2. **Compression (Level 0.5)**: Lossy per-source digests under `self-wiki/compression/` — path mirrors `raw/`, ≤~80 lines.
3. **Synthesis (Level 1)**: Integrated themes and patterns in `self-wiki/wiki/`. (Pattern Recognition)
4. **Principle/Mental Model (Level 2)**: Compressed, actionable "source code" for my life. (High Utility/Low Volume)

## Structure Rules
- `self-wiki/raw/`: Input (L0). Read-only. Three folders: `_posts/`, `origin-apple-notes/`, `twitter/`.
- `self-wiki/compression/`: Lossy digests (L0.5). Path mirrors `raw/`. Written by Composer digest (default) or `make compress`.
- `self-wiki/wiki/`: Compounding themes & principles (L1–L2).
- `self-wiki/discovery/`, `gap/`, `evolution/`: Periodic agent reports (P3).
- `self-wiki/outputs/`: Query snapshots and dialogue.
- `self-wiki/log/sources.json`: Twitter likes catalog (`type/external`) — not your beliefs.
- `self-wiki/log/pending/`: Harness builds JSON here; skills read `user_message` from pending files.
- `self-wiki/log/INDEX.json` + `log/index.md`: Machine index (auto); `self-wiki/INDEX.md`: human Obsidian hub.
- `twin/PROFILE.md`: Digital twin snapshot (post-ingest).


## Agent Skills (Operational Mandates)

### Composer digest (default — no `make compress`)
- **Action**: In Cursor, digest changed raw → `compression/` using `skills/ingest-summary.md` or `ingest-thoughts.md`.
- **Provenance**: Every digest ends with `- (Source: [[raw/origin-apple-notes/…]])` or `[[raw/_posts/…]]` — always include the `raw/` prefix.
- **Language**: Match source language (Chinese → Chinese, English → English).
- **Twitter**: `register-reference` only.
- **After**: `make post-ingest`.
- **Progress**: `make progress` — all stages (compression, discovery, gap, evolution, …) with resume commands. Detail: `log/PROGRESS.md`, `log/pipeline_progress.json`.

### Python batch ingest (`make compress`) — opt-in only
- Requires `ALLOW_PYTHON_LLM=1`. Prefer Composer for quality.

### `sync-wiki` (`make sync`) — legacy
- **Action**: Ingest `raw/` into `wiki/` via deprecated `ingest.md`. Prefer compress + post-ingest.

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
- **Traceability**: Every claim must link to its origin `(Source: [[raw/origin-apple-notes/…]])` or `[[raw/_posts/…]]`.
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
2. **Explicit Interpretation**: When the AI identifies a pattern that isn't explicitly stated, label it `[AI Synthesis]` or `[Socratic Observation]`. In `compression/`, grounded paraphrase needs no tag — tag only inferred lines.
3. **Language Fidelity**: Match the input language perfectly. Chinese source → Chinese output; English source → English output. Do not translate between English/Chinese unless asked. Applies to `compression/`, `wiki/`, `outputs/`, and agent reports.
4. **Socratic Proactivity**: If a new note reveals a blind spot, bias, or contradiction, flag it as a "Cognitive Shift".
5. **Context Efficiency**: Keep wiki files concise. If a file gets too long, refactor into sub-topics.
6. **Traceability**: Never "hallucinate" a principle; every Level 2 insight must be grounded in Level 0/1 evidence. Use blockquotes for direct evidence.
