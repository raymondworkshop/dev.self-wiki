# dev.self-wiki

Personal wiki, second brain, and Socratic Mirror.

## workflow

Drop notes into `self-wiki/raw/`, then:

```bash
make sync
make query Q="what are my values?"
make audit LINT=1
```

`make query` prints a `make promote …` hint when the answer flags `[Cognitive Shift]` or `[Socratic Observation]` (disable with `PROMOTE_SUGGEST=0`).

Weekly (optional):

```bash
make reflect
```

Also useful: `make site` · `make publish` · `make help`

### Publish (Cloudflare Pages)

Production URL is `https://<CLOUDFLARE_PAGES_PROJECT>.pages.dev`.

One-time setup:

```bash
npm i -g wrangler && wrangler login
wrangler pages project create self-mirror --production-branch=main
make publish
```

## Setup (once)

```bash
python3 -m venv .selfwikienv && .selfwikienv/bin/pip install -r requirements.txt
cp .env.example .env
```

Minimal `.env`:

```bash
GEMINI_API_KEY=your-key-here
LLM_PROVIDER=mlx
ALLOW_PYTHON_LLM=1
```


## Model

`raw/` → `wiki/` → `make ingest` → `self-wiki/twin/PROFILE.md`

- `raw/`: source truth (append only)
- `wiki/`: themes and principles
- trust layer (`ingest`): memex graph, backlinks, index, twin

Ingest can be Composer-first (Cursor skills) or batch (`make sync`).

## Advanced commands

`make wiki-synthesize` · `make wiki-synthesize-apple-notes` · `make fix-provenance` · `make ingest` · `make progress` · `make wiki-synth-status` · `make agents` · `make promote FILE=… TARGET=… CONFIRM=1` · `make doctor-config` · `make test`

Override provider: `LLM_PROVIDER=gemini make sync` · check: `make doctor-config`

## Safety rules

- Never do `raw/` → `wiki/` in one step.
- After manual wiki edits, run `make ingest`.
- Do `discover` before `gap` (or just run `make agents`).
- Do not edit `raw/` via automation.

Standards: [AGENTS.md](AGENTS.md) · design: [design.md](design.md)

## License  
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.