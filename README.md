# dev.self-wiki

Personal wiki, and Socratic Mirror.

## Daily

Drop notes into `raw/`, then:

```bash
make sync                                          # changed raw → wiki, then ingest
make query Q="what are my values?"                 # wiki Socratic mirror
make trace Q="what are my core values?"            # matching raw paragraphs + cites
make audit LINT=1
```

Weekly: `make reflect`. Site: `make site` · `make publish`. Everything else: `make help`.

`make query` suggests `make promote …` when the answer flags a cognitive shift.   
`make trace` does not write an answer; `make trace-start` serves it at `:8791`.

## Setup

```bash
python3 -m venv .selfwikienv && .selfwikienv/bin/pip install -r requirements.txt
cp .env.example .env
```

## Model

`raw/` → `wiki/` → `make ingest` 

- `raw/` — source truth (append only)
- `wiki/` — themes and principles
- ingest — memex graph, backlinks, index, twin

## Safety

- Never jump `raw/` → `wiki/` in one step.
- After manual wiki edits, run `make ingest`.
- Run `discover` before `gap` (or `make agents`).
- Do not edit `raw/` via automation.

Standards: [AGENTS.md](AGENTS.md) · design: [design.md](design.md)

## License

© 2026 Bean Workshop Ltd.
