---
last_updated: 2024-05-29T00:00:00Z
title: Tools and System Maintenance
description: Documentation regarding the maintenance and operational tools for the Self-Wiki system.
tags: [type/principle, habit, operational]
---

> This page serves as the operational manual for the Self-Wiki system, detailing the functions and protocols for knowledge management. It outlines the specific roles of various maintenance commands and the structure for knowledge integration.

## Evolution
- Initialized upon the establishment of the Self-Wiki Operating Manual, defining the necessary maintenance commands (`sync-wiki`, `audit-wiki`, `query-wiki`) and file structure.

## Content
### Agent Skills (Tool Definitions)

#### `sync-wiki`
- **Description**: Scans `raw/`, processes new insights into `wiki/`, and updates `INDEX.md`.
- **Implementation**: `make sync`

#### `audit-wiki`
- **Description**: Checks for red links, stale content, contradictions, and cognitive shifts.
- **Implementation**: `make audit`

#### `query-wiki`
- **Description**: Summarize the key insights and findings related to the query based on `wiki/`, including references to the original sources from `raw/`.
- **Implementation**: `make query`

### Wiki Standards Summary
- **File Structure**: `raw/` (unprocessed), `wiki/` (organized knowledge), `outputs/` (reports/analysis).
- **Wiki File Requirements**: One topic per file, YAML front matter (`last_updated`, `title`, `description`, `tags`), summary block (`>`), `## Evolution` section, `## Backlinks` section, and `sources` list.
- **Traceability**: All abstract ideas must link back to specific `raw/` sources.
- **Taxonomy**: Use `type/source`, `type/synthesis`, `type/principle`, or `type/evolution` as the primary tag.

## Backlinks
<!-- BEGIN BACKLINKS -->
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/origin-apple-notes/tools.md]]