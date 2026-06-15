# dev.self-wiki

Personal AI-powered wiki, Second Brain, and Socratic Mirror.

Python CLI + Gemini (or MLX last-resort) runs compress, agents, query, and the trust layer. Skills live in `skills/`; `make` wires `scripts/cli.py`.

## Setup

```bash
python3 -m venv .selfwikienv && .selfwikienv/bin/pip install -r requirements.txt
cp .env.example .env
```

Minimal `.env`:

```bash
QUERY_LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
ALLOW_PYTHON_LLM=1          # compress + discover / gap / evolution
INGEST_LLM_PROVIDER=gemini  # optional; Makefile defaults to gemini
```

```bash
make register-reference   # twitter → log/sources.json (once)
make help                 # all targets
```

## Knowledge layers

| Layer | Path | What |
|-------|------|------|
| L0 Raw | `self-wiki/raw/` | Source material (read-only for AI) |
| L0.5 Compression | `self-wiki/compression/` | Lossy digests, path mirrors `raw/` |
| L1–L2 Wiki | `self-wiki/wiki/` | Themes & principles → `twin/PROFILE.md` |
| Agents | `discovery/`, `gap/`, `evolution/` | Pattern / gap / state reports |

## Pipeline (`make`)

```
raw/  ──compress──►  compression/  ──post-ingest──►  INDEX + twin + backlinks
                          │
                          ▼
                    agents (discover → gap → evolution)
                          │
                          ▼
                       wiki/  ──post-ingest──►  L2 → twin
```

| Step | Command |
|------|---------|
| 1. Twitter catalog | `make register-reference` |
| 2. raw → compression | `make compress` or `make build` |
| 3. Trust layer | `make post-ingest` |
| 4. Agents | `make agents` |
| 5. Audit | `make audit` or `make audit LINT=1` |
| Status | `make progress` |

Drop new files under `self-wiki/raw/_posts/`, `origin-apple-notes/`, or `twitter/` before step 2.

Detail: [docs/PIPELINE.md](docs/PIPELINE.md) · standards: [AGENTS.md](AGENTS.md)

## Commands

Same as `make help`.

| Command | What |
|---------|------|
| `make post-ingest` | Backlinks, INDEX, twin |
| `make audit` | Compliance → `audit.md` |
| `make audit LINT=1` | Above + cognitive lint (Gemini) |
| `make progress` | Pipeline status + resume hints |
| `make all` | `post-ingest` + `audit` |
| `make register-reference` | Twitter catalog (no LLM) |
| `make compress` | raw → `compression/` |
| `make compress-status` | Per-file compression checklist |
| `make build` | register + compress + post-ingest + audit |
| `make extract-twitter` | Twitter `.js` → `raw/` |
| `make discover` | `discovery/{date}.md` |
| `make gap` | `gap/{date}.md` |
| `make evolution` | `evolution/{date}.md` |
| `make agents` | discover → gap → evolution |
| `make query Q="…"` | Ask wiki (Gemini) |
| `make query-web` | Browser UI |
| `make test` | Unit tests |

**Compress options:** `LIMIT=50` `FORCE=1` `FOLDER=_posts` `POST_INGEST=1`

## Batch skills (how `make` uses Gemini)

```
prepare_*.py  →  log/pending/*.json  →  run_skill.py + skills/*.md  →  output file
```

| Target | Skill | Output |
|--------|-------|--------|
| `make compress` | `ingest-summary.md` / `ingest-thoughts.md` | `compression/` |
| `make discover` | `discovery.md` | `discovery/{date}.md` |
| `make gap` | `gap.md` | `gap/{date}.md` |
| `make evolution` | `evolution.md` | `evolution/{date}.md` |

Query/lint use Gemini with only `GEMINI_API_KEY` (no `ALLOW_PYTHON_LLM`).

## Workflows

**New raw files:**

```bash
make compress LIMIT=50 POST_INGEST=1
# or full backfill:
make build
```

**Weekly:**

```bash
make progress
make agents
make post-ingest && make audit LINT=1
```

**Ask:**

```bash
make query Q="what are my values?"
```

## Layout

```
self-wiki/
  raw/           L0 input
  compression/   L0.5 digests
  wiki/          L1–L2 themes
  discovery/ gap/ evolution/
  log/           manifest, index, pending
twin/            PROFILE.md, principles.json
skills/          LLM instructions
scripts/         cli.py harness
```

## Docs

- [docs/PIPELINE.md](docs/PIPELINE.md) — step-by-step
- [AGENTS.md](AGENTS.md) — wiki standards
- [ARCHITECTURE.md](ARCHITECTURE.md) — system design

## Avoid

| Don't | Do instead |
|-------|------------|
| Skip `GEMINI_API_KEY` | Set in `.env` for query / batch |
| Skip `ALLOW_PYTHON_LLM=1` | Required for `compress` / `agents` |
| Skip `post-ingest` | Backlinks and twin go stale |
| `make gap` before `discover` | gap reads latest discovery report |
| Edit `raw/` from automation | Append new files only |
