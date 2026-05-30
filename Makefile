# Self Wiki Base Automation

PYTHON = .selfwikienv/bin/python3
LLM_PROVIDER ?= mlx
QUERY_LLM_PROVIDER ?= $(LLM_PROVIDER)
QUERY_WEB_HOST ?= 127.0.0.1
QUERY_WEB_PORT ?= 5050

.PHONY: help sync audit push test-llm query-web

help:
	@echo "self-wiki Commands:"
	@echo "  make sync    - Get the prompt to synchronize wiki/ from raw/ sources"
	@echo "  make audit   - Get the prompt to perform a wiki lint/audit"
	@echo "  make backliner - Run the backliner script"
	@echo "  make test    - Test wiki compliance"
	@echo "  make test-llm  - Test the configured LLM provider connection"
	@echo "  make query     - Query your Second Brain"
	@echo "  make query-web - Start the local FastAPI query UI"
	@echo "  make push      - Commit and push all changes"

# --- Workflow Targets ---

# DESIGN: Gemini designs/updates the engine (via Gemini CLI)
design:
	@echo "Design phase is managed by Gemini CLI to maintain the operating manual."

# RUN: Local MLX server executes the work (Production Engine)
sync:
	LLM_PROVIDER=$(LLM_PROVIDER) $(PYTHON) scripts/sync_wiki.py
	$(PYTHON) scripts/refresh_index.py

# AUDIT: Gemini audits the quality of local execution (Quality Control)
audit:
	$(PYTHON) scripts/test_wiki_compliance.py
	LLM_PROVIDER=$(LLM_PROVIDER) $(PYTHON) scripts/audit_wiki.py

# FULL CYCLE
all: sync audit


backliner:
	$(PYTHON) scripts/backliner.py


test:
	$(PYTHON) scripts/test_wiki_compliance.py

query:
	@read -p "Query your Second Brain: " q; LLM_PROVIDER=$(QUERY_LLM_PROVIDER) $(PYTHON) scripts/query_wiki.py "$$q"

query-web:
	LLM_PROVIDER=$(QUERY_LLM_PROVIDER) QUERY_WEB_HOST=$(QUERY_WEB_HOST) QUERY_WEB_PORT=$(QUERY_WEB_PORT) $(PYTHON) scripts/query_server.py

test-llm:
	LLM_PROVIDER=$(LLM_PROVIDER) $(PYTHON) scripts/test_llm_conn.py

push:
	git add .
	git commit -m "self-wiki update: $$(date +'%Y-%m-%d')"
	git push
