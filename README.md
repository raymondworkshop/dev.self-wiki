# dev.self-wiki

Personal wiki, second brain, and Socratic Mirror.

## Daily workflow

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

Also useful: `make query-web` · `make help`

### Weekly automation (optional)

```bash
chmod +x scripts/launchd-weekly.sh
cp launchd/com.zhaowenlong.self-wiki-weekly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.zhaowenlong.self-wiki-weekly.plist
```

Runs `make sync` then `make reflect` every **Sunday 04:00**. Logs: `self-wiki/log/launchd-weekly.log`. Requires `.env` with `GEMINI_API_KEY` and `ALLOW_PYTHON_LLM=1`.

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

`make reflect` (discover → gap → evolution) uses **Gemini by default** when `GEMINI_API_KEY` is set. Override with `AGENT_LLM_PROVIDER=mlx` or force cloud: `LLM_PROVIDER=gemini make reflect`. MLX remains last-resort fallback when cloud fails.

Twitter catalog once: `make register-reference`

## Model

`raw/` → `compression/` → `wiki/` → `post-ingest` → `twin/PROFILE.md`

- `raw/`: source truth (append only)
- `compression/`: per-source digests
- `wiki/`: themes and principles
- trust layer (`post-ingest`): backlinks, index, twin

Ingest can be Composer-first (Cursor skills) or batch (`make sync`).

## Advanced commands

`make compress` · `make wiki-synthesize` · `make wiki-synthesize-apple-notes` · `make fix-provenance` · `make post-ingest` · `make progress` · `make wiki-synth-status` · `make agents` · `make promote FILE=… TARGET=… CONFIRM=1` · `make doctor-config` · `make test`

Override provider: `LLM_PROVIDER=gemini make sync` · check: `make doctor-config`

## Safety rules

- Never do `raw/` → `wiki/` in one step.
- After manual wiki edits, run `make post-ingest`.
- Do `discover` before `gap` (or just run `make agents`).
- Do not edit `raw/` via automation.

Standards: [AGENTS.md](AGENTS.md) · design: [design.md](design.md)

## License  
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.