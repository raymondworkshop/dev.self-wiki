# Skills

| Skill | Trigger | Output |
|-------|---------|--------|
| [wiki-synthesize.md](wiki-synthesize.md) | `make sync` / `make wiki-synthesize` | JSON actions → `wiki/` |
| [query.md](query.md) | `make query` | `outputs/` answer |
| [lint.md](lint.md) | `make audit LINT=1` | merge into `audit.md` |
| [discovery.md](discovery.md) | `make discover` | `discovery/` report |
| [gap.md](gap.md) | `make gap` | `gap/` report |
| [evolution.md](evolution.md) | `make evolution` | `evolution/` report |

**Agents pipeline:** `make agents` = discover → gap → evolution. `make reflect` = agents + ingest + audit LINT=1.

**Pipeline:** `raw/` → `wiki/` (wiki-synthesize) → `make ingest`.

Profiles: [ingest-profiles.yaml](ingest-profiles.yaml) · routing: [skill-registry.yaml](skill-registry.yaml)
