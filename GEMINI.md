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
2. **Synthesis (Level 1)**: Integrated themes and patterns derived from multiple raw sources. (Pattern Recognition)
3. **Principle/Mental Model (Level 2)**: Compressed, actionable "source code" for my life. (High Utility/Low Volume)

## Structure Rules
- `self-wiki/raw/`: Input stream. Read-only for AI. Never modify raw files.
- `self-wiki/wiki/`: The "Second Brain". AI-curated, structured, and cross-linked.
- `self-wiki/outputs/`: Snapshots of reasoning, reports, and deep-dives.

## Agent Skills (Operational Mandates)

### `sync-wiki` (`make sync`)
- **Action**: Ingest `raw/`, identify patterns, update/create `wiki/` entries.
- **Note**: Focus on *lossy compression*—discard the fluff, capture the core insight.

### `audit-wiki` (`make audit`)
- **Action**: Scan for "Emotional Triggers", "Cognitive Shifts" (contradictions), "Stale Wisdom", and "Red Links".
- **Socratic Duty**: Prompt the user when a new insight contradicts an old principle or habit.

### `query-wiki` (`make query`)
- **Action**: Reason over the entire wiki to answer complex life queries.
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
1. **Fidelity to Raw Truth**: The AI must never "hallucinate" a belief, preference, or event. Every claim in the `wiki/` must be a direct distillation of `raw/` evidence.
2. **Explicit Interpretation**: When the AI identifies a pattern that isn't explicitly stated (e.g., an underlying anxiety), it must label it as `[AI Synthesis]` or `[Socratic Observation]` to distinguish it from "raw truth".
3. **Language Fidelity**: Match the input language perfectly. Do not translate between English/Chinese unless asked.
4. **Socratic Proactivity**: If a new note reveals a blind spot, bias, or contradiction, flag it as a "Cognitive Shift".
5. **Context Efficiency**: Keep wiki files concise. If a file gets too long, refactor into sub-topics.
6. **Traceability**: Never "hallucinate" a principle; every Level 2 insight must be grounded in Level 0/1 evidence. Use blockquotes for direct evidence.
