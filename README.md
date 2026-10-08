# dev.self-wiki

Personal wiki, and Socratic Mirror.

## Workflow

Drop notes into `self-wiki/raw/`, then:

```bash
make sync
make query Q="what are my values?"          # wiki Socratic mirror
make trace Q="what are my core values?"    # raw-only facts + cites (default gpt)
make audit LINT=1
```

`make query` suggests `make promote …` when the answer flags `[Cognitive Shift]` or `[Socratic Observation]` (`PROMOTE_SUGGEST=0` to disable).

`make trace` answers from `self-wiki/raw/` only (keyword paragraph retrieval → `skills/trace.md`). Follows symlink dirs (e.g. `raw/_posts`), skips generated `raw/qa/`, and drops identical content copies (e.g. `raw/twitter` vs `_posts/twitter`). Index rebuild is incremental (only changed files; `FORCE=1` for full). Chinese queries use 2–3-gram terms. Cites need path + `#pN` + lines + verbatim quote. Twitter hits → `[Twitter Reference]`. Default LLM: **gpt**. Scoped (`SCOPE=` / `@file`): top‑16 keyword hits + ±2 neighbors (no whole-file pad). **Trace** is a standalone product (peer to Echo `:5050`): `make trace-start` → Tailscale `http://100.90.225.26:8791/` (PWA; `POST /ask`, `GET /source?id=raw/…#pN`, `GET /health`; bind `0.0.0.0`, no auth).

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
LLM_MODEL=gpt
LLM_CLOUD_MODEL=gpt
LLM_MODEL_FALLBACK=mlx
ALLOW_PYTHON_LLM=1
ALLOW_LOCAL_LLM=1
```

| Alias | Upstream | Notes |
|-------|----------|--------|
| `gpt` | `openai/gpt-oss-120b` | **default** — Western + ZDR |
| `mlx` | local Qwen3.5 | fallback when gpt fails |
| `cloud` | expands to `LLM_CLOUD_MODEL` | same as `gpt` unless you change it |
| `ultra` | Nemotron 3 Ultra `:free` | opt-in only (weaker privacy) |

`LLM_PROVIDER=mlx` is a legacy alias for `local-gateway`. Default is `gpt` → `mlx` (myblog raw via symlink stays off ultra). Use `LLM_MODEL=ultra make query` only when you accept free-provider privacy. Gateway cloud paths use `reasoning=medium`, ~8192 tokens, and keep skill system prompts. Legacy `nemotron` → ultra.

Gemini works in code but is not recommended in HK (geo-block).

## Model

`raw/` → `wiki/` → `make ingest` → `twin/PROFILE.md`

- `raw/` — source truth (append only)
- `wiki/` — themes and principles
- ingest — memex graph, backlinks, index, twin

Ingest can be Composer-first (Cursor skills) or batch (`make sync`).

## Advanced

`make wiki-synthesize` · `make wiki-synthesize-apple-notes` · `make fix-provenance` · `make ingest` · `make progress` · `make wiki-synth-status` · `make agents` · `make promote FILE=… TARGET=… CONFIRM=1` · `make doctor-config` · `make test`

Overrides: `LLM_PROVIDER=openrouter make sync` · `LLM_MODEL=cloud make query` · `QUERY_LLM_MODEL=ultra` · `TRACE_LLM_MODEL=mlx make trace`

## Safety

- Never jump `raw/` → `wiki/` in one step.
- After manual wiki edits, run `make ingest`.
- Run `discover` before `gap` (or `make agents`).
- Do not edit `raw/` via automation.

Standards: [AGENTS.md](AGENTS.md) · design: [design.md](design.md)

## License

© 2026 Bean Workshop Ltd.
