# My Self-Wiki Operating Manual  

## Purpose
reflect and expand my thought to foster self-discovery, emotional regulation, and deeper cognitive engagement.

Used for self-awareness, emotional processing, and personal growth. It serves as a dynamic repository of my evolving understanding of myself and the world, helping me to integrate insights from various sources and experiences into a coherent framework for living.

## Category

- self: Awareness, stoic integration, vulnerability, self-acceptance
- work: Strategic execution, minimalism, and professional development
- relationship: Emotional maturity, authentic connection, and boundary management
- habit: Sustainable habits, operational frameworks, and system efficiency
- growth-trajectory: Synthesis of long-term life patterns, personal evolution, and transformation insights


## Context
- Topic: a Socratic Mirror 
- Goal: Build a comprehensive, interconnected wiki to foster self-discovery, emotional regulation, and deeper cognitive engagement. This is used for self-awareness, emotional processing, and personal growth. 
- Sources: A mix of diary entries, notes from books and articles, and reflections on experiences. This includes both raw, unprocessed thoughts and more polished reflections.
- Output: A well-organized wiki that captures the depth and breadth of myself-knowledge, with clear connections between topics and a structure that allows for easy navigation and continuous growth. The wiki should be dynamic, evolving as new insights are gained and new sources are added. 


## Structure Rules  
- self-wiki/raw/ contains unprocessed source material. Never modify raw files.
- self-wiki/wiki/ is the organized knowledge base. AI maintains this entirely.
- self-wiki/outputs/ stores generated reports and analysis.

## Agent Skills (Tool Definitions)

### `sync-wiki`
- **Description**: Scans `raw/`, processes new insights into `wiki/`, and updates `INDEX.md`.
- **Implementation**: `make sync`

### `audit-wiki`
- **Description**: Checks for red links, stale content, contradictions, and cognitive shifts.
- **Implementation**: `make audit`

### `query-wiki`
- **Description**: Summarize the key insights and findings related to the query based on `wiki/`, including references to the original sources from `raw/`
- **Implementation**: `make query` 

## Wiki Standards
- One topic per file in wiki/ 
- Every file must include a YAML front matter block containing `last_updated` (ISO 8601 format), `title`, `description`, and `tags`
- Every file starts with a blank line, followed by '>' and a 2-3 sentence summary, and ends with `sources`  (list of file paths from `raw/`)   
- Every file must have an `## Evolution` section tracking changes in perspective over time.
- **Traceability Requirement**: Every abstract idea, principle, or conceptual model must explicitly link back to its specific source raw files. If a wiki page synthesizes multiple raw notes, every major conceptual point must be able to trace its origin to at least one entry in the `sources` list.
- **Backliner System**: Every file must contain a `## Backlinks` section, maintained by the system, using the format:
  ```markdown
  ## Backlinks
  <!-- BEGIN BACKLINKS -->
  - **Evolved from**: [[Topic]]
  - **Mentioned in**: [[Topic]]
  - **Contradicts**: [[Topic]]
  <!-- END BACKLINKS -->
  ```
- **Provenance Tracking**: When synthesizing a principle, use a blockquote or annotation to link to the specific file: `(Source: [[file-path]])`.
- **Taxonomy Standards**: Every note must include one primary tag indicating its functional nature:
  - `type/source`: Unprocessed raw notes.
  - `type/synthesis`: Notes that integrate multiple sources.
  - `type/principle`: Core mental models or life philosophies.
  - `type/evolution`: Records of cognitive shifts.
- INDEX.md maintained alphabetically, updated with every change
- When new raw sources arrive, update all relevant wiki articles
- Never translate the source language. Match the output language to the input language perfectly
- Flag contradictions between sources as "Cognitive Shifts" in the audit.


## Output Format  
When I ask for a report: Summary (3 sentences)  → Key Findings → Supporting Evidence . 
When I ask for a recommendation: Context → Options (max 3) → Recommendation .
When I ask for a comparison: Topic A → Topic B → Similarities → Differences → Conclusion .
When I ask for an analysis: Subject → Analysis Framework → Key Insights → Implications → Conclusion .
