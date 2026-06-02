# dev.self-wiki

Personal **compile-first** wiki + digital twin workspace. Raw notes → structured wiki → query / audit.

Architecture: [ARCHITECTURE.md](ARCHITECTURE.md) · Operating manual: [GEMINI.md](GEMINI.md)

## Quick start

```bash
python3 -m venv .selfwikienv && .selfwikienv/bin/pip install -r requirements.txt
cp .env.example .env    # LLM_PROVIDER, LLM_URL, keys
make sync               # ingest changed raw → wiki
make query Q="what are my values?"
make query-web          # browser UI (same query pipeline)
```

## Commands

| Command | What it does |
|---------|----------------|
| `make sync` | Ingest changed raw → wiki |
| `make query` | Ask wiki; saves to `self-wiki/outputs/` |
| `make audit` | Compliance tests + deterministic `audit.md` |
| `make audit LINT=1` | Above + one global cognitive lint (LLM) |
| `make query-web` | Web UI: ask + browse Wiki / Outputs / Profile |

Advanced (Cursor mode, promote, twin, …): `python scripts/cli.py --help`

Override provider: `LLM_PROVIDER=gemini make query` · `LLM_PROVIDER=openai make query`

## Project structure

```
skills/           Prompts (ingest, query, lint) + query profiles
scripts/          Harness (cli, run_skill) + deterministic tooling
self-wiki/
  raw/            Input — never modified by automation
  wiki/           Compiled second brain
  outputs/        Query answers & reports
  log/pending/    Skill input packages (JSON)
  log/INDEX.json  Machine topic index
GEMINI.md         Philosophy, wiki standards, skill resolver
twin/             Digital twin PROFILE (post-ingest)
archive/          Legacy archive notes (_self-wiki removed from repo)
```

## Skills (where intelligence lives)

| Skill | Makefile | Output |
|-------|----------|--------|
| [skills/ingest.md](skills/ingest.md) | `make sync` | JSON `actions[]` → wiki pages |
| [skills/query.md](skills/query.md) | `make query`, `query-web` | Markdown answer + provenance |
| [skills/lint.md](skills/lint.md) | `make lint` | Cognitive lint section |

Retrieval profiles: [skills/query-profiles.yaml](skills/query-profiles.yaml)

## Interactive (Cursor) workflow

```bash
python scripts/cli.py prepare-ingest          # or prepare-query "…"
# Open self-wiki/log/pending/*.json + matching skills/*.md in chat
python scripts/cli.py apply-ingest --file …
python scripts/cli.py post-ingest
```

See `python scripts/cli.py --help` for promote, twin, lint, etc.

## License / privacy

Local-first by default (`LLM_PROVIDER=mlx`). Raw and wiki stay on disk under `self-wiki/`.
