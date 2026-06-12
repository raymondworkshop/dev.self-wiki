
#### self-wiki  

##### tasks  

- make    
    > make sync
    > make query
    > make audit
    > make audit LINT=1
    > LLM_PROVIDER=gemini make query

- site
    > make query-web
    > http://100.90.225.26:5050/

- advanced
    > python scripts/cli.py --help

- docs
    > [README.md](README.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [AGENTS.md](AGENTS.md)


## Project structure

```
skills/           Prompts (ingest, query, lint) + query profiles
scripts/          Harness (cli, run_skill) + deterministic tooling
self-wiki/
  raw/            Input — never modified by automation
  wiki/           Compiled second brain
  outputs/        Query answers & reports
  log/pending/    Skill input packages (JSON)
  log/INDEX.json  Machine topic index
AGENTS.md         Philosophy, wiki standards, agent mandates
twin/             Digital twin PROFILE (post-ingest)
archive/          Legacy archive notes (_self-wiki removed from repo)
```

## Skills (where intelligence lives)

| Skill | Makefile | Output |
|-------|----------|--------|
| [skills/ingest.md](skills/ingest.md) | `make sync` | JSON `actions[]` → wiki pages |
| [skills/query.md](skills/query.md) | `make query`, `query-web` | Markdown answer + provenance |
| [skills/lint.md](skills/lint.md) | `make lint` | Cognitive lint section |

Retrieval profiles: [skills/query-profiles.yaml](skills/query-profiles.yaml)

## Interactive (Cursor) workflow

```bash
python scripts/cli.py prepare-ingest          # or prepare-query "…"
# Open self-wiki/log/pending/*.json + matching skills/*.md in chat
python scripts/cli.py apply-ingest --file …
python scripts/cli.py post-ingest
```

See `python scripts/cli.py --help` for promote, twin, lint, etc.


##### the architecture
* Push intelligence up into skills, and push execution down into deterministic tooling. keep the harness thin.  
    - Fast skills sit on top
        + markdown procedures that **encode judgement, process, and domain knowledge** 
    - thin cli harness sits in the middle.
        + JSON in, text out. Read-only by default.
    - deterministic is where trust lives. 
        + Same input, same output. Every time. SQL queris. Compiled code. ARITHMETIC.

* a skill file tell the model how
    - works like a method call 

* the harness is the program that runs the LLM  
    - runs the model in a loop,
    reads and writes your files, manages context, and enforces safety.

* Resolvers tell it what to load and when  
    - The description is the resolver.
    Every skill has a description field, and the model matches user intent to skill descriptions automatically.

* latent space vs deterministic space  
    - latent spcae is where intelligence lives
    - deterministic is where trust lives  

* Diarization is the step that makes AI useful for real knowledge work

#### references
* [Thin Harness, Fat Skills](https://x.com/garrytan/status/2042925773300908103)
