# Self Wiki — Python CLI

.DEFAULT_GOAL := help

PY  := .selfwikienv/bin/python3
CLI := $(PY) scripts/cli.py
API := QUERY_LLM_PROVIDER=$(or $(QUERY_LLM_PROVIDER),gemini)
LLM := ALLOW_PYTHON_LLM=1

COMPRESS_OPTS := $(if $(LIMIT),--limit $(LIMIT)) $(if $(FORCE),--force) \
	$(if $(FOLDER),--folder $(FOLDER)) $(if $(POST_INGEST),--post-ingest)

.PHONY: help post-ingest audit progress all \
	register-reference compress compress-status build extract-twitter \
	discover gap evolution agents query query-web test

post-ingest:
	$(CLI) post-ingest

audit:
	$(PY) scripts/test_wiki_compliance.py
	$(PY) scripts/audit_wiki.py
ifdef LINT
	$(API) $(CLI) lint
endif

progress:
	$(CLI) progress

all: post-ingest audit

register-reference:
	$(CLI) register-reference

compress:
	$(LLM) INGEST_LLM_PROVIDER=$(or $(INGEST_LLM_PROVIDER),$(QUERY_LLM_PROVIDER),gemini) \
		$(CLI) compress $(COMPRESS_OPTS)

compress-status:
	$(CLI) progress --compression-only $(if $(FOLDER),--folder $(FOLDER),)

build: register-reference
	$(LLM) INGEST_LLM_PROVIDER=gemini $(CLI) compress --provider gemini --post-ingest
	$(MAKE) audit

extract-twitter:
	$(PY) scripts/extract_twitter_raw.py

discover gap evolution:
	$(LLM) $(CLI) $@

agents: discover gap evolution

query:
ifdef Q
	$(API) $(CLI) query "$(Q)"
else
	@read -p "Query: " q; $(API) $(CLI) query "$$q"
endif

query-web:
	$(PY) scripts/query_server.py

test:
	@for f in scripts/test_*.py; do $(PY) "$$f" || exit 1; done

help:
	@echo "make post-ingest          backlinks, INDEX, twin"
	@echo "make audit [LINT=1]       compliance (+ optional lint)"
	@echo "make progress             pipeline status"
	@echo "make all                  post-ingest + audit"
	@echo ""
	@echo "make register-reference   twitter catalog"
	@echo "make compress             raw → compression  (LIMIT FOLDER FORCE POST_INGEST)"
	@echo "make compress-status      compression checklist"
	@echo "make build                register + compress + post-ingest + audit"
	@echo "make extract-twitter      twitter .js → raw/"
	@echo ""
	@echo "make discover             discovery/{date}.md"
	@echo "make gap                  gap/{date}.md"
	@echo "make evolution            evolution/{date}.md"
	@echo "make agents               discover → gap → evolution"
	@echo ""
	@echo "make query [Q=\"...\"]      ask wiki (gemini)"
	@echo "make query-web            browser UI"
	@echo "make test                 unit tests"
	@echo ""
	@echo "Docs: docs/PIPELINE.md  CLI: $(CLI) --help"
