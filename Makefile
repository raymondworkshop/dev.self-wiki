# Self Wiki — three commands

PYTHON = .selfwikienv/bin/python3
CLI = $(PYTHON) scripts/cli.py
LLM_PROVIDER ?= mlx
# Query/lint providers: set QUERY_LLM_PROVIDER / LINT_LLM_PROVIDER in .env (see .env.example)

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
	$(CLI) query "$(Q)"
else
	@read -p "Query your Second Brain: " q; \
	$(CLI) query "$$q"
endif

query-web:
	$(PYTHON) scripts/query_server.py

audit:
	$(PYTHON) scripts/test_wiki_compliance.py
	$(PYTHON) scripts/audit_wiki.py
ifdef LINT
	$(CLI) lint
endif

extract-twitter:
	$(PYTHON) scripts/extract_twitter_raw.py

test:
	$(PYTHON) scripts/test_wiki_compliance.py
	$(PYTHON) scripts/test_query_server.py
	$(PYTHON) scripts/test_promote_output.py
	$(PYTHON) scripts/test_audit_wiki.py
	$(PYTHON) scripts/test_extract_twitter_raw.py
	$(PYTHON) scripts/test_build_twin_profile.py
	$(PYTHON) scripts/test_twin_profile_excerpt.py

all: sync audit
