---
last_updated: 2026-05-04T00:00:00Z
title: My Self-Wiki Operating Manual
description: Defines the purpose, structure, rules, and agent skills for the Self-Wiki project, serving as a Socratic Mirror for self-discovery.
tags: [type/principle, self, habit]
---

> This document outlines the operational framework for the Self-Wiki, establishing it as a dynamic, interconnected knowledge base designed to foster self-discovery, emotional regulation, and deeper cognitive engagement. It functions as a Socratic Mirror, moving beyond simple knowledge retrieval to facilitate a continuous feedback loop of inquiry.

## Purpose
The Self-Wiki serves as a dynamic repository for integrating insights from various sources (diary, books, experiences) into a coherent framework for personal growth. Its core functions are:
- **Self-Awareness**: Deep introspection into one's patterns and beliefs.
- **Emotional Processing**: Providing a structured space to navigate and process complex emotional data.
- **Cognitive Engagement**: Constantly challenging and refining one's understanding of self and the world.

## Category Mapping
- **self**: Awareness, stoic integration, vulnerability, self-acceptance
- **work**: Strategic execution, minimalism, and professional development
- **relationship**: Emotional maturity, authentic connection, and boundary management
- **habit**: Sustainable habits, operational frameworks, and system efficiency
- **growth-trajectory**: Synthesis of long-term life patterns, personal evolution, and transformation insights

## Project Structure & Workflow
The system enforces a strict separation of concerns:
- `raw/`: Contains unprocessed, original source material. **Never modify.**
- `wiki/`: The AI-maintained, organized knowledge base.
- `outputs/`: Stores generated reports, analyses, and actionable outputs.

**Agent Skills (Tool Definitions):**
- `sync-wiki`: Processes `raw/` into `wiki/` and updates `INDEX.md`. (`make sync`)
- `audit-wiki`: Checks for cognitive shifts, contradictions, and stale content. (`make audit`)
- `query-wiki`: Summarizes findings based on a query, linking back to `raw/` sources. (`make query`)

## Wiki Standards & Traceability
- **File Structure**: One topic per file in `wiki/`.
- **Front Matter**: Every file requires YAML metadata (`last_updated`, `title`, `description`, `tags`).
- **Content Flow**: Starts with a blank line, followed by `>` and a 2-3 sentence summary, and concludes with `sources` (listing `raw/` paths).
- **Evolution Tracking**: Must include an `## Evolution` section tracking perspective shifts.
- **Traceability**: All abstract ideas must explicitly link back to their specific source files using `(Source: [[file-path]])`.
- **Backliner System**: Must include a system-maintained `## Backlinks` section tracking relationships between concepts.
- **Taxonomy**: Each note must have a primary functional tag (`type/source`, `type/synthesis`, `type/principle`, `type/evolution`).

## Output Formatting Rules
- **Report**: Summary (3 sentences) $\rightarrow$ Key Findings $\rightarrow$ Supporting Evidence.
- **Recommendation**: Context $\rightarrow$ Options (max 3) $\rightarrow$ Recommendation.
- **Comparison**: Topic A $\rightarrow$ Topic B $\rightarrow$ Similarities $\rightarrow$ Differences $\rightarrow$ Conclusion.
- **Analysis**: Subject $\rightarrow$ Analysis Framework $\rightarrow$ Key Insights $\rightarrow$ Implications $\rightarrow$ Conclusion.

## Cognitive Shift Protocol
Contradictions found during `audit-wiki` must be flagged as "Cognitive Shifts."

## Sources
- [[self-wiki/raw/diary/2026-05-04-self-wiki.md]] (This file contains the initial operational context and the current data dump.)