# dev.self-wiki

Personal wiki, second brain, and Socratic Mirror.

## Workflow

Drop notes into `self-wiki/raw/`, then:

```bash
make sync
make query Q="what are my values?"          # wiki Socratic mirror
make rbrain Q="what are my core values?"    # raw-only facts + verbatim cites
make audit LINT=1
```

`make query` suggests `make promote …` when the answer flags `[Cognitive Shift]` or `[Socratic Observation]` (`PROMOTE_SUGGEST=0` to disable).

`make rbrain` answers from `self-wiki/raw/` only (keyword paragraph retrieval → `skills/rbrain.md`). Cites need path + `#pN` + lines + verbatim quote. Twitter hits → `[Twitter Reference]`. HTTP: `make rbrain-serve` (`POST /ask`, `GET /source?id=raw/…#pN`).

Weekly: `make reflect` · also `make site` · `make publish` · `make help`

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

| Alias | Upstream | Notes |
|-------|----------|--------|
| `mlx` | local Qwen3.5 | fast / private / fallback |
| `gemma4` | `google/gemma-4-31b-it` | **default** (quality) |
| `laguna` | `poolside/laguna-m.1` | coding only — not for wiki |

`LLM_PROVIDER=mlx` is a legacy alias for `local-gateway`. Prefer `gemma4` + `mlx` fallback. Gateway uses `reasoning=high`, 4096–8192 tokens, and keeps skill system prompts. Legacy `nemotron` → gemma4.

Gemini works in code but is not recommended in HK (geo-block).

## Model

`raw/` → `wiki/` → `make ingest` → `twin/PROFILE.md`

- `raw/` — source truth (append only)
- `wiki/` — themes and principles
- ingest — memex graph, backlinks, index, twin

Ingest can be Composer-first (Cursor skills) or batch (`make sync`).

## Advanced

`make wiki-synthesize` · `make wiki-synthesize-apple-notes` · `make fix-provenance` · `make ingest` · `make progress` · `make wiki-synth-status` · `make agents` · `make promote FILE=… TARGET=… CONFIRM=1` · `make doctor-config` · `make test`

Overrides: `LLM_PROVIDER=openrouter make sync` · `LLM_MODEL=laguna make query` · `QUERY_LLM_MODEL=gemma4`

## Safety

- Never jump `raw/` → `wiki/` in one step.
- After manual wiki edits, run `make ingest`.
- Run `discover` before `gap` (or `make agents`).
- Do not edit `raw/` via automation.

Standards: [AGENTS.md](AGENTS.md) · design: [design.md](design.md)

## License

MIT — see [LICENSE](LICENSE).
