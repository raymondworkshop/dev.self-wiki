
#### self-wiki  

##### ideas  
- add memex in self-wiki, remove compression step

- the result is not practical, especially when I build memex in blog  

##### tasks  

- daily → [README.md](README.md#daily-workflow)
- weekly → `make reflect` (or `make agents` for reports only)
- site → `make site` · `http://100.90.225.26:8787/`
- docs → [README.md](README.md) · [design.md](design.md) · [AGENTS.md](AGENTS.md) · [skills/README.md](skills/README.md)

Runs `make sync` → `make reflect` every **Sunday 04:00**. Logs: `self-wiki/log/launchd-weekly.log`. Requires `.env` with `GEMINI_API_KEY` and `ALLOW_PYTHON_LLM=1`. Publish manually when ready: `make publish`.

##### the architecture
* Push intelligence up into skills, and push execution down into deterministic tooling. keep the harness thin.  
    - See [design.md](design.md) for layout, pipeline, and trust layer.

#### references
* [Thin Harness, Fat Skills](https://x.com/garrytan/status/2042925773300908103)
