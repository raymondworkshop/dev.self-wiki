# Architecture: dev.self-wiki

> **Thin harness, fat skills.** Prompts and judgement live in `skills/`; Python prepares context, runs skills, and applies deterministic tooling.

## Three layers

| Layer | Role | Location |
|-------|------|----------|
| **Skills** | Prompts, profiles, lint rules, output formats | `skills/*.md`, `skills/query-profiles.yaml` |
| **Harness** | CLI / web entry, `run_skill` (only LLM call site per unit) | `scripts/cli.py`, `scripts/run_skill.py`, `scripts/query_server.py` |
| **Tooling** | Hash cache, merge, index, backlinks, compliance | `scripts/orchestrator.py`, `apply_ingest.py`, `backliner.py`, … |

```mermaid
flowchart TB
  subgraph skills [Skills]
    Ingest[skills/ingest.md]
    Query[skills/query.md]
    Lint[skills/lint.md]
  end

  subgraph harness [Harness]
    CLI[scripts/cli.py]
    RunSkill[scripts/run_skill.py]
    Web[scripts/query_server.py]
  end

  subgraph tooling [Deterministic tooling]
    Orch[orchestrator.py]
    Apply[apply_ingest.py]
    Back[backliner.py]
    Index[refresh_index.py]
  end

  Raw[self-wiki/raw] --> Orch
  Orch --> CLI
  CLI --> RunSkill
  RunSkill --> skills
  RunSkill --> Apply
  Apply --> Wiki[self-wiki/wiki]
  CLI --> Back --> Index --> Twin[build_twin_profile.py]
  Twin --> Profile[twin/PROFILE.md]
  CLI --> Pending[pending_cleanup.py]
  Pending --> PendingDir[log/pending]
  Web --> QueryEngine[query_engine.py] --> RunSkill
  QueryEngine --> Profile
  Promote[promote_output.py] --> Wiki
```

## Repository layout

```
dev.self-wiki/
├── skills/                    # Fat skills (prompts only)
│   ├── ingest.md
│   ├── query.md
│   ├── lint.md
│   └── query-profiles.yaml
├── scripts/
│   ├── cli.py                 # Main harness: sync, query, lint, prepare-*
│   ├── run_skill.py           # Load skill + pending → LLM once
│   ├── config.py              # Paths, .env
│   │
│   ├── prepare_ingest.py      # Raw → pending JSON (no LLM)
│   ├── apply_ingest.py        # actions[] → wiki (WikiPage)
│   ├── orchestrator.py        # Raw file hash cache
│   ├── pending_cleanup.py     # Pending JSON pair cleanup + prune
│   ├── wiki_themes.py
│   ├── refresh_index.py       # INDEX.json + log/index.md
│   ├── log_utils.py
│   ├── backliner.py
│   │
│   ├── prepare_query.py       # Retrieval pack → pending JSON
│   ├── query_retrieval.py     # Profile detect, rank, evidence
│   ├── query_engine.py        # Query pipeline + save + interactive CLI
│   ├── query_server.py        # FastAPI: ask + browse
│   │
│   ├── audit_wiki.py          # Deterministic audit report
│   ├── prepare_lint.py        # Context for global lint
│   ├── build_twin_profile.py  # Twin snapshot + query/lint excerpts
│   ├── promote_output.py      # Query output → wiki (compound loop)
│   │
│   ├── models.py              # WikiPage schema
│   ├── llm_provider.py
│   ├── extract_twitter_raw.py # Twitter .js → raw markdown
│   └── test_*.py
│
├── self-wiki/                 # Knowledge store
│   ├── raw/                   # Level 0 — read-only input (_posts, origin-apple-notes, twitter)
│   ├── compression/           # Level 0.5 — per-source digests (path mirrors raw/)
│   ├── wiki/                  # Level 1–2 — compiled themes
│   ├── discovery/             # Unknown-known reports (P3)
│   ├── gap/                   # Unknown-unknown reports (P3)
│   ├── evolution/             # Knowledge-state metrics (P3)
│   ├── outputs/               # Query snapshots, reports
│   ├── log/
│   │   ├── pending/           # Pending JSON for skills
│   │   ├── INDEX.json         # Machine index (topics)
│   │   ├── sources.json       # Twitter catalog (type/external)
│   │   ├── index.md           # Karpathy-style directory
│   │   └── log.md             # Append-only run log
│   ├── INDEX.md               # Human Obsidian hub (hand-maintained)
│   └── audit.md               # make audit + make lint output
│
├── twin/                      # PROFILE.md + principles.json (post-ingest)
├── archive/plans/             # Archived design plans (historical)
├── README.md                  # Quick start + command table
├── AGENTS.md                  # LLM operating manual (canonical for agents)
├── .env.example               # LLM + retention knobs
├── Makefile                   # make sync | query | audit | query-web | test
```

## Pipelines

### Ingest — compression path (default)

```
orchestrator / mtime check → prepare_compress → run_skill(compression) → compression/*.md
post_ingest = backliner → refresh_index → build_twin_profile → append log.md
```

Skills: [skills/ingest-summary.md](skills/ingest-summary.md), [skills/ingest-thoughts.md](skills/ingest-thoughts.md).  
Twitter: [scripts/register_reference.py](scripts/register_reference.py) → `log/sources.json` (no LLM).

### Ingest — legacy (`make sync`)

```
orchestrator (hash) → prepare_ingest → run_skill(ingest) → apply_ingest → [cleanup pair] → post_ingest
post_ingest = backliner → refresh_index → build_twin_profile → append log.md → prune stale pending
```

One LLM call per changed raw file (per skill unit). Prompt: [skills/ingest.md](skills/ingest.md).

**Pending JSON lifecycle** ([scripts/pending_cleanup.py](scripts/pending_cleanup.py)):

- After each successful `apply_ingest` in `cli.py sync`, the matching `ingest-*.json` + `ingest-actions-*.json` pair is deleted (unless `PENDING_RETAIN_ON_SUCCESS=1`).
- After `post_ingest`, pairs older than `PENDING_RETAIN_DAYS` (default 7) are pruned; failed pairs (missing actions file) are kept for debug.

After ingest, `build_twin_profile.py` writes:

- **`twin/PROFILE.md`** — compact human snapshot: top N Level-2 principles (default 80, `confidence ≥ 0.7`), **Recent evolution** (dated `## Evolution` lines from L2 / `type/shift` / high-signal entries), all **Contradicts** tensions, and recent `type/shift` pages
- **`twin/principles.json`** — full machine catalog of qualifying Level-2 principles

Query selects query-relevant principles from `principles.json` (term scoring + shifts/tensions from PROFILE) in `prepare_query`. Lint uses the JSON catalog for principle excerpts in `prepare_lint`.

### Query (`make query` / `make query-web`)

```
prepare_query (deterministic retrieval) → run_skill(query) → query_engine.save_output
```

One LLM call per question. Prompt: [skills/query.md](skills/query.md). Profiles: [skills/query-profiles.yaml](skills/query-profiles.yaml).

`prepare_query` injects query-aware twin context (top-K principles from `twin/principles.json` + shifts/tensions from PROFILE) into the pending JSON user message (deterministic, no extra LLM). Knobs: `TWIN_QUERY_PRINCIPLES_K`, `TWIN_PROFILE_EXCERPT_CHARS`.

### Compound loop (`make promote`)

```
query output (self-wiki/outputs/) → promote_output → append to wiki page + tag type/shift
next post_ingest → PROFILE picks up shift → next query reads updated twin
```

Dry-run by default; pass `--confirm` (or `CONFIRM=1` via Makefile) to merge. Promoted sections appear under `### Promoted from query` on the target wiki page.

### Audit & lint

| Command | LLM | Output |
|---------|-----|--------|
| `make audit` | No | `self-wiki/audit.md` |
| `make audit LINT=1` | Once (lint skill) | Merges cognitive section into `audit.md` |

## Entry points

| You want… | Use |
|-----------|-----|
| Full automation | `make sync`, `make query`, `make audit` |
| Cursor step-by-step | `cli.py prepare-ingest` → `run-skill` → `apply-ingest --pending …` → `post-ingest` |
| Web browse + ask | `make query-web` |
| Promote query → wiki | `cli.py promote --file … --target …` (`--confirm` to apply) |
| Rebuild twin only | `cli.py twin` |
| Twitter export → raw | `make extract-twitter` |
| Unit tests (dev) | `make test` |
| Interactive query CLI | `python scripts/query_engine.py --list` |
| Manual pending prune (rare) | `python scripts/pending_cleanup.py --prune --days N --confirm` |

## LLM discipline

| Operation | Calls |
|-----------|-------|
| sync (per changed raw) | 1× `run_skill(ingest)` |
| query (per question) | 1× `run_skill(query)` |
| lint | 0 in audit; optional 1× `run_skill(lint)` |

Provider: `.env` → `LLM_PROVIDER` (`mlx` default; `gemini`, `openai` cloud opt-in). Makefile may override per command.

## Data model

- **Raw (L0)**: Immutable source notes under `self-wiki/raw/`.
- **Synthesis (L1)**: Integrated themes in `self-wiki/wiki/`.
- **Principle (L2)**: Compressed mental models in `self-wiki/wiki/` with `type/principle`.

Wiki pages enforced via `WikiPage` ([scripts/models.py](scripts/models.py)): YAML front matter, Socratic summary, Evolution, Sources, Backlinks.

## Testing

| Test | Command |
|------|---------|
| All unit tests | `make test` (compliance, query-server, promote, audit, twitter, twin) |
| Wiki + audit (CI-style) | `make audit` |
| LLM connectivity | `python scripts/test_llm_conn.py` |

## Removed / consolidated (sprawl reduction)

| Was | Now |
|-----|-----|
| `sync_wiki.py` | `make sync` / `cli.py sync` |
| `query_wiki.py`, `save_query_output.py` | `query_engine.py` |
| `twin_context.py` | `build_twin_profile.py` (excerpt helpers) |
| `ingest_helpers.py` | `prepare_ingest.py` |
| `GEMINI.md` | `AGENTS.md` |
