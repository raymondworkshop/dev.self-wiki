# Skills

Prompts only — no Python. The harness loads these via [scripts/run_skill.py](../scripts/run_skill.py).

| File | Used by | Output |
|------|---------|--------|
| [ingest-summary.md](ingest-summary.md) | `make compress` (`_posts`) | Markdown → `compression/` |
| [ingest-thoughts.md](ingest-thoughts.md) | `make compress` (apple-notes) | Markdown → `compression/` |
| [ingest.md](ingest.md) | legacy `make sync` | JSON `actions[]` → wiki |
| [query.md](query.md) | `make query`, `query-web` | Markdown answer |
| [lint.md](lint.md) | `make lint` | Markdown lint section |
| [ingest-profiles.yaml](ingest-profiles.yaml) | `compress`, profile router | Folder → skill routing |
| [query-profiles.yaml](query-profiles.yaml) | `prepare_query` (deterministic) | Retrieval + profile hints |

**Default ingest:** Composer digest or `make compress` → `compression/` → `make post-ingest`.

See [ARCHITECTURE.md](../ARCHITECTURE.md) for pipelines.
