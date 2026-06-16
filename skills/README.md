# Skills

Prompts only — no Python. The harness loads these via [scripts/run_skill.py](../scripts/run_skill.py).

| File | Used by | Output |
|------|---------|--------|
| [ingest-summary.md](ingest-summary.md) | `make compress` / `make sync` (`_posts`) | Markdown → `compression/` |
| [ingest-thoughts.md](ingest-thoughts.md) | `make compress` / `make sync` (apple-notes) | Markdown → `compression/` |
| [wiki-synthesize.md](wiki-synthesize.md) | `make wiki-synthesize` | JSON `actions[]` → `wiki/` |
| [discovery.md](discovery.md) | `make discover` | Markdown → `discovery/` |
| [gap.md](gap.md) | `make gap` | Markdown → `gap/` |
| [evolution.md](evolution.md) | `make evolution` | Markdown → `evolution/` |
| [query.md](query.md) | `make query`, `query-web` | Markdown answer |
| [lint.md](lint.md) | `make lint` | Markdown lint section |
| [ingest-profiles.yaml](ingest-profiles.yaml) | `compress`, `sync`, profile router | Folder → skill routing |
| [query-profiles.yaml](query-profiles.yaml) | `prepare_query` (deterministic) | Retrieval + profile hints |
| [skill-registry.yaml](skill-registry.yaml) | all pending builders | Stage → skill routing overrides |

**Pipeline:** `raw/` → `compression/` (skill 1) → `wiki/` (skill 2: wiki-synthesize) → `make post-ingest`.

`skill-registry.yaml` is optional; if present, it decouples stage routing from Python code.
You can change stage skills without editing scripts.

See [design.md](../design.md).
