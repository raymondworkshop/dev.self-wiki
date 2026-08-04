
#### self-wiki  

##### ideas  
- todo  
    +  Twin chatbot = outward "chat like me" persona (ideal: others talk to a version of you)  
    + Socratic query = inward self-awareness (limits, motivations, inconsistencies, blind spots)  
        - Q&A from wiki/

-  rbrain — `make rbrain` / `make rbrain-serve` (raw-only + verbatim cites)
    - Q&A from raw/ 
    - 专有数据当唯一事实库 → 可审计问答 → 支撑法律 / 金融 / 医疗的合规与风控  
    
- add memex in self-wiki, remove compression step

- the result is not practical, especially when I build memex in blog  

##### tasks  

- daily → [README.md](README.md#daily-workflow)
- weekly → `make reflect` (or `make agents` for reports only)
- site → `make site` · `http://100.90.225.26:8787/`
- docs → [README.md](README.md) · [design.md](design.md) · [AGENTS.md](AGENTS.md) · [skills/README.md](skills/README.md)

Runs `make sync` → `make reflect` every **Sunday 04:00**. Logs: `launchd/launchd-weekly.log` (stdout/err); runtime state in repo-root `log/` + `twin/`. Requires `.env` with `ALLOW_PYTHON_LLM=1`. Publish manually when ready: `make publish`.

##### the architecture
* Push intelligence up into skills, and push execution down into deterministic tooling. keep the harness thin.  
    - See [design.md](design.md) for layout, pipeline, and trust layer.

#### references
* [Thin Harness, Fat Skills](https://x.com/garrytan/status/2042925773300908103)
