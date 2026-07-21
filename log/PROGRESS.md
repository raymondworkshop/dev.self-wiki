# Pipeline progress

Updated: 2026-07-20T09:36:42.859921+00:00

Machine index: `log/pipeline_progress.json`
Wiki-synthesize detail: `log/wiki_synth_manifest.json`

## Cycle

- **Status:** in_progress
- **Resume stage:** `wiki_synthesize`
- **Resume command:** `make wiki-synthesize LIMIT=20`
- **Completed:** register_reference, discovery, gap, evolution, ingest, audit

### Last stop

- **Stage:** ingest
- **Status:** done
- **At:** 2026-07-20T09:36:42.859532+00:00

## Stages

| Stage | Status | Done / detail | Resume |
|-------|--------|---------------|--------|
| [x] register_reference | done | 23959 twitter entries | — |
| [ ] wiki_synthesize | pending | 0/0 raw files | `make wiki-synthesize LIMIT=20` |
| [x] discovery | done | log/reports/discovery/2026-07-20.md | — |
| [x] gap | done | log/reports/gap/2026-07-20.md | — |
| [x] evolution | done | log/reports/evolution/2026-07-20.md | — |
| [x] ingest | done | vault changed since last memex ingest — run make ingest | — |
| [x] audit | done | self-wiki/audit.md | — |

## Resume cheatsheet

```bash
make progress              # refresh + print
make wiki-synthesize LIMIT=20
make wiki-synthesize LIMIT=20
make wiki-synthesize FOLDER=origin-apple-notes LIMIT=30
make ingest
make discover && make gap && make evolution
make audit
```
