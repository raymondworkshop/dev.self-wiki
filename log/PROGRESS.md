# Pipeline progress

Updated: 2026-08-17T04:14:14.288594+00:00

Machine index: `log/pipeline_progress.json`
Wiki-synthesize detail: `log/wiki_synth_manifest.json`

## Cycle

- **Status:** in_progress
- **Resume stage:** `wiki_synthesize`
- **Resume command:** `make wiki-synthesize LIMIT=20  # 188 pending/failed`
- **Completed:** register_reference, discovery, gap, evolution, ingest, audit

### Last stop

- **Stage:** ingest
- **Status:** done
- **At:** 2026-08-17T04:14:14.288494+00:00

## Stages

| Stage | Status | Done / detail | Resume |
|-------|--------|---------------|--------|
| [x] register_reference | done | 23959 twitter entries | — |
| [ ] wiki_synthesize | in_progress | 201/1066 raw files (188 left) | `make wiki-synthesize LIMIT=20  # 188 pending/failed` |
| [x] discovery | done | self-wiki/discovery/2026-08-17.md | — |
| [x] gap | done | self-wiki/gap/2026-08-17.md | — |
| [x] evolution | done | self-wiki/evolution/2026-08-17.md | — |
| [x] ingest | done | vault changed since last memex ingest — run make ingest | — |
| [x] audit | done | self-wiki/audit.md | — |

## Resume cheatsheet

```bash
make progress              # refresh + print
make wiki-synthesize LIMIT=20  # 188 pending/failed
make wiki-synthesize LIMIT=20
make wiki-synthesize FOLDER=origin-apple-notes LIMIT=30
make ingest
make discover && make gap && make evolution
make audit
```

## Wiki-synthesize (summary)

- done: 0 · no_actions: 201 · pending: 183 · failed: 5
