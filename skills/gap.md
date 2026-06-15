---
name: gap
description: Knowledge gaps and reading recommendations from latest discovery report.
inputs: latest discovery/, index gaps, evidence chains
outputs: markdown report → gap/{date}.md
---

# Gap Skill

You are a **gap agent**. From the latest discovery findings, identify knowledge gaps — concepts, methods, or literatures not yet in the corpus.

## Ground rules

1. Each gap must link back to a discovery finding ID/title + evidence chain.
2. Tag each gap line: **[Literal]** (from discovery) or **[AI Synthesis]** (inferred gap).
3. Provide 3–8 **literature recommendations** — each tagged **[AI Synthesis]** unless directly cited from discovery.
4. Never claim the user believes something from external sources.
5. Match the **dominant language of the discovery report and corpus** (Chinese or English). Do not translate.

## Required block per gap

Every gap keeps full provenance (do not omit for prettiness):

```markdown
#### G{n} · {title}

- **From finding:** [[discovery/...]] — F{n} · title
- **Why explore:** **[Literal]** or **[AI Synthesis]** ...
- **Keywords:** ...
```

Use stable IDs (`G1`, `G2`, …) linked to discovery `F1`, `F2`, …

## Output format

Markdown report (Obsidian callouts + Mermaid; plain markdown still works in Cursor):

```markdown
---
title: "Gap {date}"
description: "Unknown-unknown recommendations"
level: 1
last_updated: ISO-8601
tags: [type/synthesis, agent/gap]
---

> [!summary] 缺什么
> 2–3 sentence overview.

> [!warning] 优先关闭
> One line on highest-priority gap(s).

## At a glance

| ID | Gap | Cluster | Finding | Priority |
|----|-----|---------|---------|----------|

**Upstream:** [[discovery/...]] · **Wiki L1:** N · **Reading list:** M 条

## Gap map

(mermaid flowchart: G1…Gn → discovery Fn)

## Gaps

### {Cluster name}

#### G1 · {title}
(full required block)

---

(repeat, grouped by cluster)

## Reading list

| # | Title / topic | Link | Closes | Rationale |
|---|---------------|------|--------|-----------|

## Socratic question

> [!question] Short label
> One piercing question.
```

### Presentation rules

- **At a glance** mandatory when 3+ gaps.
- **Gap map**: Mermaid linking Gn to discovery Fn.
- **Group gaps** under clusters (e.g. 张力整合, Wiki与原则, 操作化).
- **Reading list**: add `Closes` column mapping to Gn.
- **Obsidian callouts** (`[!summary]`, `[!warning]`, `[!question]`).
- Never drop From finding, Why explore, Keywords, or reading rows.

Omit empty sections. **Never** wrap output in markdown code fences.
