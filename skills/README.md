# Skills

Prompts only — no Python. The harness loads these via [scripts/run_skill.py](../scripts/run_skill.py).

| File | Used by | Output |
|------|---------|--------|
| [ingest.md](ingest.md) | `make sync` | JSON `actions[]` |
| [query.md](query.md) | `make query`, `query-web` | Markdown answer |
| [lint.md](lint.md) | `make lint` | Markdown lint section |
| [query-profiles.yaml](query-profiles.yaml) | `prepare_query` (deterministic) | Retrieval + profile hints in pending JSON |

See [ARCHITECTURE.md](../ARCHITECTURE.md) for pipelines.

## Future work

- Skill registry (`skills/registry.yaml` + `skill_resolver.py`) for pattern-matched skill selection beyond fixed ingest/query/lint.
