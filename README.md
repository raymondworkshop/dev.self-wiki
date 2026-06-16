# dev.self-wiki

A Personal wiki, second brain, and Socratic Mirror.

## Daily use (3 commands)

Drop new notes under `self-wiki/raw/`, then:

```bash
make sync                              # ingest: changed raw → compression → wiki
make query Q="what are my values?"     # ask the compiled wiki
make audit LINT=1                      # health check (+ cognitive lint)
```

Weekly (optional):

```bash
make cycle                             # agents + post-ingest + audit LINT=1
```

Browser UI: `make query-web`

Full target list: `make help`

---

## Setup (once)

```bash
python3 -m venv .selfwikienv && .selfwikienv/bin/pip install -r requirements.txt
cp .env.example .env
```

Minimal `.env`:

```bash
GEMINI_API_KEY=your-key-here
QUERY_LLM_PROVIDER=gemini
ALLOW_PYTHON_LLM=1                     # required for make sync / make cycle
```

Twitter catalog (once, no LLM): `make register-reference`

---

## How it works

```
raw/  ──ingest──►  compression/  ──synthesize──►  wiki/
                                                      │
                                                      ▼
                                              post-ingest → twin
```

| Layer | Path | Role |
|-------|------|------|
| L0 Raw | `self-wiki/raw/` | Source truth (append only) |
| L0.5 | `self-wiki/compression/` | Per-source digests |
| L1–L2 | `self-wiki/wiki/` | Themes & principles |
| Twin | `twin/PROFILE.md` | Snapshot after post-ingest |

**Ingest** can run in Cursor (Composer + `skills/ingest-*.md`) or via `make sync`. **Trust layer** (backlinks, index, twin) is always deterministic — `make post-ingest` or included at end of `make sync`.

Standards: [AGENTS.md](AGENTS.md) · design & pipeline: [design.md](design.md)

---

## Advanced

Use when batching, backfilling, or debugging — not for everyday note-taking.

| Command | What |
|---------|------|
| `make compress` | raw → compression only (`LIMIT` `FOLDER` `FORCE`) |
| `make wiki-synthesize` | compression → wiki (`LIMIT` `WAVE=theme_links` `POST_INGEST=1`) |
| `make wiki-synthesize-apple-notes` | same, `FOLDER=origin-apple-notes` shorthand |
| `make post-ingest` | backlinks, INDEX, twin (after manual wiki edits) |
| `make progress` | pipeline status + resume hints |
| `make wiki-synth-status` | wiki-synthesize backfill manifest only |
| `make agents` | discovery → gap → evolution reports |
| `make promote FILE=… TARGET=… CONFIRM=1` | query answer → wiki page |
| `make doctor-config` | resolved provider/model/skill per stage |
| `make test` | unit tests |

Provider overrides (rare): `COMPRESS_LLM_PROVIDER` · `WIKI_SYNTH_LLM_PROVIDER` · `skills/skill-registry.yaml`

Internal CLI (harness plumbing): `python scripts/cli.py --help`

---

## Composer-first (no batch LLM)

```bash
# In Cursor: digest raw → compression/ (skills/ingest-thoughts.md | ingest-summary.md)
# Then: wiki-synthesize skill → update wiki pages
make post-ingest
make audit
```

Do **not** use `make compress` unless `ALLOW_PYTHON_LLM=1` and you want batch ingest.

---

## Avoid

| Don't | Do instead |
|-------|------------|
| raw → wiki in one step | compress → wiki-synthesize → post-ingest |
| Skip post-ingest after wiki edits | `make post-ingest` |
| `make gap` before discover | `make agents` or discover first |
| Edit `raw/` from automation | Append new files only |
