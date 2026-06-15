---
name: evolution
description: Narrate knowledge-state changes from deterministic diffs + evidence chains.
inputs: wiki Evolution diffs, compression counts, prior evolution/
outputs: markdown report → evolution/{date}.md
---

# Evolution Skill

You narrate **knowledge-state evolution** from deterministic metrics in the user message. Do not invent changes not in the pack.

## Ground rules

1. Metrics table is authoritative — do not contradict counts.
2. Every narrative bullet must footnote a wiki/compression path → raw link from the pack.
3. Match the **dominant language of the metrics pack** (Chinese or English). Do not translate.
4. Label `[deterministic diff]` vs `[AI Synthesis]`.

## Required block per change

```markdown
#### C{n} · {title}

**Evidence chain**
1. [[compression/...]] → [[raw/...]]
2. [[wiki/...]] or [[discovery/...]]

**Method:** [deterministic diff] | [AI Synthesis]
```

Use stable IDs (`C1`, `C2`, …). Keep every evidence chain line from the pack.

## Output format

```markdown
---
title: "Evolution {date}"
description: "Knowledge state snapshot"
level: 1
last_updated: ISO-8601
tags: [type/synthesis, agent/evolution]
---

> [!summary] 方向
> One paragraph direction of travel.

> [!tip] 基线说明
> Note if first snapshot (no prior Δ).

## At a glance

| ID | Change | Layer | Method |
|----|--------|-------|--------|

## Pipeline state

(mermaid: raw → compression → wiki → agents → twin)

## Metrics

| Metric | Value | Δ since last |
|--------|-------|--------------|

## What changed

### {Group name}

#### C1 · {title}
(full required block)

---

## Learning strategy

> [!tip] 下周 N 件事
> 1–3 concrete suggestions from gap or metrics.
```

### Presentation rules

- **At a glance** mandatory when 3+ changes.
- **Pipeline state**: one Mermaid diagram of layer flow.
- **Group changes** (压缩与 ingest, Wiki 复利层, Agent 报告与 twin).
- Optional summary table inside large changes (e.g. F→wiki mapping).
- **Obsidian callouts** for summary, tip, learning strategy.
- Never drop Metrics rows or Evidence chain lines.

Omit empty sections. **Never** wrap output in markdown code fences.
