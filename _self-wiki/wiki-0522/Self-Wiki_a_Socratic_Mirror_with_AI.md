---
title: 'Self-Wiki: a Socratic Mirror with AI'
last_updated: '2026-05-20T20:51:35.167286'
description: Defines the architecture and operational mandate of the Self-Wiki system,
  detailing the roles of the Gemini (Strategic) and Local MLX (Operational) components
  in achieving high-signal self-reflection.
level: 1
tags:
- type/principle
- cognitive_modeling
- system_architecture
alias: 'Self-Wiki: a Socratic Mirror with AI'
---

> This entry establishes the operational philosophy of the Self-Wiki, positioning the AI as a 'Socratic Mirror' rather than a simple answer engine. Its function is to facilitate deep cognitive engagement, emotional regulation, and self-discovery through an iterative feedback loop.

The structure mandates that the AI integrates raw inputs into a persistent, searchable knowledge base, moving from mere data logging to psychological integration.



### Distillation (2026-05-20) - source: [[../raw/diary/2026-05-04-self-wiki.md]]
## Operating Philosophy: The Socratic Mirror
This wiki functions as a Reasoning Engine and a Socratic Mirror, treating the LLM as the OS and the wiki as the high-resolution Context Window.

**Dual-Model Workflow**:
- **Gemini (Strategic)**: Architectural design, system auditing, knowledge synthesis strategy.
- **Local MLX (Operational)**: Routine data processing, file synchronization (`make sync`), and synthesis execution based on Gemini’s architecture.

**Goal**: To foster self-discovery, emotional regulation, and deep cognitive engagement through iterative distillation.

**Knowledge Hierarchy (The Distillation Loop)**:
1. **Raw (Level 0)**: Unprocessed thoughts, logs, diary entries, and external clippings. (High Entropy/Volume)
2. **Synthesis (Level 1)**: Integrated themes and patterns derived from multiple raw sources. (Pattern Recognition)
3. **Principle/Mental Model (Level 2)**: Compressed, actionable 'source code' for my life. (High Utility/Low Volume)

**Structure Rules**:
- `self-wiki/raw/`: Input stream. Read-only for AI.
- `self-wiki/wiki/`: The 'Second Brain'. AI-curated, structured, and cross-linked.
- `self-wiki/outputs/`: Snapshots of reasoning, reports, and deep-dives.

**Agent Skills (Operational Mandates)**:
- `sync-wiki` (`make sync`): Ingest `raw/`, identify patterns, update/create `wiki/` entries, focusing on lossy compression.
- `audit-wiki` (`make audit`): Scan for "Emotional Triggers", "Cognitive Shifts", "Stale Wisdom", and "Red Links", prompting the user on contradictions.
- `query-wiki` (`make query`): Reason over the entire wiki to answer complex life queries, providing Synthesis + Provenance.

**Wiki Standards (LLM-Optimized)**:
- **One Topic Per File**: Modularity enforced.
- **YAML Front Matter**: Includes `last_updated`, `title`, `description`, `level`, and `tags`.
- **Socratic Summary**: Every file begins with a blockquote capturing the essence.
- **Traceability**: Every claim links to its origin `(Source: [[raw-file-path]])`.
- **Evolution Section**: Tracks how ideas have changed over time.
- **Backlinks**: Automated cross-referencing.

**Taxonomy (Functional Tags)**:
- `type/source`, `type/synthesis`, `type/principle`, `type/shift`.

**Core Mandates**:
1. **Fidelity to Raw Truth**: No hallucination of belief or event.
2. **Explicit Interpretation**: Label AI synthesis clearly (`[AI Synthesis]`).
3. **Language Fidelity**: Match input language perfectly.
4. **Socratic Proactivity**: Flag blind spots as "Cognitive Shift".
5. **Context Efficiency**: Refactor long files into sub-topics.
6. **Traceability**: Level 2 insights must be grounded in Level 0/1 evidence.


## Evolution


## Backlinks


## Sources
- [[../raw/diary/2026-05-04-self-wiki.md]]
