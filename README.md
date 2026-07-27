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

Minimal `.env` (local LLM via [dev.local-ai](../dev.local-ai) gateway `:8080`):

```bash
LLM_PROVIDER=local-gateway
LLM_URL=http://127.0.0.1:8080/v1/chat/completions
LLM_MODEL=gemma4
LLM_MODEL_FALLBACK=mlx
ALLOW_PYTHON_LLM=1
ALLOW_LOCAL_LLM=1
```

`LLM_PROVIDER=mlx` is still accepted as a legacy alias for `local-gateway`.

Gateway model aliases (same URL; set `LLM_MODEL`):

| Alias | Upstream (via gateway) | Notes |
|-------|------------------------|--------|
| `mlx` | local Qwen3.5 | fast / private / fallback |
| `gemma4` | `google/gemma-4-31b-it` (paid) | **default** for wiki query/sync (quality) |
| `laguna` | `poolside/laguna-m.1` | paid coding only — not for wiki synthesize |

Recommended: `LLM_MODEL=gemma4` + `LLM_MODEL_FALLBACK=mlx`. Gateway uses **`reasoning=high`**, floor **4096** / cap **8192** tokens, and **does not overwrite** skill system prompts. Legacy `nemotron` still routes to gemma4.

Or OpenAI / OpenRouter (if you prefer direct cloud API over the gateway):

```bash
OPENROUTER_API_KEY=your-key-here
LLM_PROVIDER=openrouter
```

Gemini is still supported in code but **not recommended in HK** (geo-block). Default: **local-gateway** + **gemma4**.


## Model

`raw/` → `wiki/` → `make ingest` → `twin/PROFILE.md`

- `raw/`: source truth (append only)
- `wiki/`: themes and principles
- trust layer (`ingest`): memex graph, backlinks, index, twin

Ingest can be Composer-first (Cursor skills) or batch (`make sync`).

## Advanced commands

`make wiki-synthesize` · `make wiki-synthesize-apple-notes` · `make fix-provenance` · `make ingest` · `make progress` · `make wiki-synth-status` · `make agents` · `make promote FILE=… TARGET=… CONFIRM=1` · `make doctor-config` · `make test`

Override provider: `LLM_PROVIDER=openrouter make sync` · `LLM_MODEL=laguna make query` · `QUERY_LLM_MODEL=gemma4` (query default via gateway) · check: `make doctor-config`

## Safety rules

- Never do `raw/` → `wiki/` in one step.
- After manual wiki edits, run `make ingest`.
- Do `discover` before `gap` (or just run `make agents`).
- Do not edit `raw/` via automation.

Standards: [AGENTS.md](AGENTS.md) · design: [design.md](design.md)

## License  
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.