
#### self-wiki  

##### ideas  
- the result is not practical, especially when I build memex in blog  
  

##### tasks  

- daily
    > make sync
    > make query Q="..."
    > make audit LINT=1
    > make reflect                  # periodic review

- site
    > make query-web
    > http://100.90.225.26:5050/

- advanced
    > make help
    > python scripts/cli.py --help

- docs
    > [README.md](README.md) · [design.md](design.md) · [AGENTS.md](AGENTS.md)


## Project structure

```
skills/           Prompts (ingest-summary, ingest-thoughts, query, lint) + profiles
scripts/          Harness (cli, run_skill) + deterministic tooling
self-wiki/
  raw/            Input — never modified (_posts, origin-apple-notes, twitter)
  compression/    L0.5 digests (path mirrors raw/)
  wiki/           Compiled second brain (L1–L2)
  discovery/      Unknown-known reports
  gap/            Knowledge gap reports
  evolution/      Knowledge-state over time
  outputs/        Query answers & reports
  log/pending/    Skill input packages (JSON)
  log/sources.json  Twitter catalog
  twin/             Digital twin PROFILE (post-ingest)
```

## Skills

| Skill | Command | Output |
|-------|---------|--------|
| [ingest-summary.md](skills/ingest-summary.md) | `make compress` / `make sync` | `compression/_posts/…` |
| [ingest-thoughts.md](skills/ingest-thoughts.md) | `make compress` / `make sync` | `compression/origin-apple-notes/…` |
| [wiki-synthesize.md](skills/wiki-synthesize.md) | `make wiki-synthesize` | `wiki/` updates |
| [query.md](skills/query.md) | `make query` | Markdown + provenance |

## Workflow (Composer-first)

```bash
make register-reference
# In Composer: digest raw → compression/ (skills/ingest-thoughts.md | ingest-summary.md)
# Provenance: (Source: [[raw/origin-apple-notes/foo.md]])
make post-ingest
make audit
```


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
