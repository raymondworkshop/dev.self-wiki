
#### self-wiki  

##### ideas  
- todo  
    + rbrain — 慢慢让 AI 知道自己是谁、记住自己、长出自己的**写文章风格**  
        - 「声音」= prose voice（文章怎么写），不是口语腔调
        - 写出来越来越是「我自己」——不是装出来的角色
        - process: raw → wiki → PROFILE 定信念骨架；写风从自己的 raw 文章范例复利
        - 对外代表 = 长成之后的副产物（later / optional）
        - ≠ rdatabase（事实库问答）；≠ Socratic query（向内照镜子）


-  rdatabase — `make rdatabase` / `make rdatabase-serve` (raw-only + verbatim cites)
    - Q&A from raw/ 
    - 专有数据当唯一事实库 → 可审计问答 → 支撑法律 / 金融 / 医疗的合规与风控  

- Socratic query = inward self-awareness (limits, motivations, inconsistencies, blind spots)  
    - Q&A from wiki/
    
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
