# Self Wiki — three commands

PYTHON = .selfwikienv/bin/python3
CLI = $(PYTHON) scripts/cli.py
LLM_PROVIDER ?= mlx
QUERY_LLM_PROVIDER ?= $(LLM_PROVIDER)

.DEFAULT_GOAL := help

.PHONY: help sync query audit query-web test all 

help:
	@echo "  make sync              raw → wiki"
	@echo "  make query [Q=\"...\"]   ask wiki"
	@echo "  make audit [LINT=1]    test wiki + report (+ optional lint)"
	@echo ""
	@echo "  make query-web         browser UI"
	@echo "  make extract-twitter   Twitter .js → raw markdown"
	@echo "  python scripts/cli.py --help   advanced / Cursor mode"

sync:
	LLM_PROVIDER=$(LLM_PROVIDER) $(CLI) sync

query:
ifdef Q
	LLM_PROVIDER=$(QUERY_LLM_PROVIDER) $(CLI) query "$(Q)"
else
	@read -p "Query your Second Brain: " q; \
	LLM_PROVIDER=$(QUERY_LLM_PROVIDER) $(CLI) query "$$q"
endif

query-web:
	LLM_PROVIDER=$(QUERY_LLM_PROVIDER) $(PYTHON) scripts/query_server.py

audit:
	$(PYTHON) scripts/test_wiki_compliance.py
	$(PYTHON) scripts/audit_wiki.py
ifdef LINT
	LLM_PROVIDER=$(LLM_PROVIDER) $(CLI) lint
endif

extract-twitter:
	$(PYTHON) scripts/extract_twitter_raw.py

test:
	$(PYTHON) scripts/test_wiki_compliance.py
	$(PYTHON) scripts/test_query_server.py
	$(PYTHON) scripts/test_promote_output.py
	$(PYTHON) scripts/test_audit_wiki.py
	$(PYTHON) scripts/test_extract_twitter_raw.py

all: sync audit
