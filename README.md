# dev.self-wiki

Personal wiki, second brain, and Socratic Mirror.

## Daily workflow

Drop notes into `self-wiki/raw/`, then:

```bash
make sync
make query Q="what are my values?"
make audit LINT=1
```

Weekly (optional):

```bash
make cycle
```

Also useful: `make query-web` · `make help`

## Setup (once)

```bash
python3 -m venv .selfwikienv && .selfwikienv/bin/pip install -r requirements.txt
cp .env.example .env
```

Minimal `.env`:

```bash
GEMINI_API_KEY=your-key-here
QUERY_LLM_PROVIDER=gemini
ALLOW_PYTHON_LLM=1
```

Twitter catalog once: `make register-reference`

## Model

`raw/` → `compression/` → `wiki/` → `post-ingest` → `twin/PROFILE.md`

- `raw/`: source truth (append only)
- `compression/`: per-source digests
- `wiki/`: themes and principles
- trust layer (`post-ingest`): backlinks, index, twin

Ingest can be Composer-first (Cursor skills) or batch (`make sync`).

## Advanced commands

`make compress` · `make wiki-synthesize` · `make wiki-synthesize-apple-notes` · `make post-ingest` · `make progress` · `make wiki-synth-status` · `make agents` · `make promote FILE=… TARGET=… CONFIRM=1` · `make doctor-config` · `make test`

Use provider overrides only when needed: `COMPRESS_LLM_PROVIDER`, `WIKI_SYNTH_LLM_PROVIDER`.

## Safety rules

- Never do `raw/` → `wiki/` in one step.
- After manual wiki edits, run `make post-ingest`.
- Do `discover` before `gap` (or just run `make agents`).
- Do not edit `raw/` via automation.

Standards: [AGENTS.md](AGENTS.md) · design: [design.md](design.md)

## License  
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.