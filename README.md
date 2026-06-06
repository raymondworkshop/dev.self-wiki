# dev.self-wiki

Personal AI-powered wiki + Second Brain.  
Raw notes → structured wiki → query / audit.


This wiki is a **Reasoning Engine** and a **Socratic Mirror**.  
We treat LLMs as the "OS" and the wiki as the "Context Window" for high-resolution self-reflection.

# privacy

Local-first by default (`LLM_PROVIDER=mlx`).  
Raw and wiki stay on disk under `self-wiki/`.


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

Override provider:  
`LLM_PROVIDER=gemini make query`  
`LLM_PROVIDER=openai make query`  


## License 
&copy; 2026 Bean Workshop Ltd.
