# Self Wiki — Python CLI

.DEFAULT_GOAL := help

.PHONY: help sync query audit query-web test all 

help:
	@echo "Daily:  sync · ingest · site · publish · query · audit · reflect"
	@echo "Pipeline:  wiki-synthesize · ingest · progress · fix-provenance"
	@echo "Memex:  make memex CMD=\"stats|missing|backlinks PAGE\""
	@echo "Agents:  discover · gap · evolution · agents"
	@echo "Other:  promote · register-reference · test · doctor-config"
	@echo ""
	@echo "  make query-web         browser UI"
	@echo "  make extract-twitter   Twitter .js → raw markdown"
	@echo "  python scripts/cli.py --help   advanced / Cursor mode"

sync:
	$(LLM_ENV) $(CLI) sync $(CLI_PROVIDER_ARG)
ifneq ($(filter 1 true yes,$(SKIP_INGEST)),)
	@echo "Skipping ingest (SKIP_INGEST=1)"
else
	$(INGEST_ENV) $(CLI) ingest $(INGEST_OPTS)
endif

fix-provenance:
	$(PY) scripts/fix_provenance_links.py $(if $(DRY),--dry-run)
	$(if $(DRY),,$(INGEST_ENV) $(CLI) ingest)

# --- agents ---
discover gap evolution:
	$(LLM_ENV) $(CLI) $@ $(CLI_PROVIDER_ARG)

agents: discover gap evolution
	@echo "Agents complete: discovery → gap → evolution"

reflect: agents ingest audit LINT=1

# --- query & publish ---
promote:
	$(CLI) promote --file $(FILE) --target $(TARGET) $(if $(CONFIRM),--confirm)

query:
ifdef Q
	$(LLM_ENV) $(CLI) query "$(Q)" $(CLI_PROVIDER_ARG)
else
	@read -p "Query: " q; $(LLM_ENV) $(CLI) query "$$q" $(CLI_PROVIDER_ARG)
endif

publish:
	$(INGEST_ENV) $(PY) scripts/publish_wiki.py \
	  $(if $(BUILD_ONLY),,--deploy) \
	  $(if $(PUBLISH_DIR),--out $(PUBLISH_DIR),) \
	  $(if $(CLOUDFLARE_PAGES_PROJECT),--project $(CLOUDFLARE_PAGES_PROJECT),)

site:
	@test -d $(SITE_DIR) || (echo "No $(SITE_DIR)/ — run: make ingest && make publish BUILD_ONLY=1" && exit 1)
	@echo ""
	@echo "Site:   http://127.0.0.1:$(SITE_PORT)/index.html"
	@echo "Memex:  http://127.0.0.1:$(SITE_PORT)/memex/index.html"
	@echo "Press Ctrl+C to stop."
	$(PY) -m http.server $(SITE_PORT) --bind 127.0.0.1 --directory $(SITE_DIR)

memex:
	$(PY) scripts/memex_cli.py $(CMD)

doctor-config:
	$(LLM_ENV) $(CLI) doctor-config $(DOCTOR_ARGS)

extract-twitter:
	$(PYTHON) scripts/extract_twitter_raw.py

test:
	$(PYTHON) scripts/test_wiki_compliance.py
	$(PYTHON) scripts/test_query_server.py
	$(PYTHON) scripts/test_promote_output.py
	$(PYTHON) scripts/test_audit_wiki.py
	$(PYTHON) scripts/test_extract_twitter_raw.py

all: sync audit
