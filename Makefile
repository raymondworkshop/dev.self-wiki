# Self Wiki — Python CLI

.DEFAULT_GOAL := help

PY  := .selfwikienv/bin/python3
CLI := $(PY) scripts/cli.py

LLM_PROVIDER ?= mlx
LLM_ENV := ALLOW_PYTHON_LLM=1 ALLOW_LOCAL_LLM=1 LLM_PROVIDER=$(LLM_PROVIDER)
CLI_PROVIDER_ARG := --provider $(LLM_PROVIDER)

INGEST_OPTS := $(if $(REPORT),--report,)
INGEST_ENV := $(if $(FAST),FAST=$(FAST),) $(if $(REPORT),REPORT=1,)

WIKI_SYNTH_OPTS := $(if $(LIMIT),--limit $(LIMIT)) $(if $(FORCE),--force) \
	$(if $(FOLDER),--folder $(FOLDER)) $(if $(WAVE),--wave $(WAVE)) \
	$(if $(INGEST),--ingest)
DOCTOR_ARGS := $(if $(RAW),--raw $(RAW),) $(CLI_PROVIDER_ARG)

SITE_PORT ?= 8787
SITE_DIR  ?= dist

.PHONY: help ingest memex audit progress register-reference sync \
	fix-provenance wiki-synthesize wiki-synthesize-apple-notes wiki-synth-status \
	discover gap evolution agents reflect promote query test \
	doctor-config publish site

help:
	@echo "Daily:  sync · ingest · site · publish · query · audit · reflect"
	@echo "Pipeline:  wiki-synthesize · ingest · progress · fix-provenance"
	@echo "Memex:  make memex CMD=\"stats|missing|backlinks PAGE\""
	@echo "Agents:  discover · gap · evolution · agents"
	@echo "Other:  promote · register-reference · test · doctor-config"
	@echo ""
	@echo "Examples:"
	@echo "  make sync              # changed raw → wiki-synthesize, then ingest"
	@echo "  make sync SKIP_INGEST=1  # wiki-synthesize only, skip ingest"
	@echo "  make ingest [FAST=1]   # memex · index · twin (no LLM)"
	@echo "  make query Q=\"what are my values?\""
	@echo "  make audit LINT=1"
	@echo "  make agents            # discover → gap → evolution"
	@echo "  make reflect           # agents + ingest + audit LINT=1"
	@echo "  make site [PORT=8787]     # serve dist/ locally (build first: ingest + publish BUILD_ONLY=1)"
	@echo "  make publish [BUILD_ONLY=1]"
	@echo ""
	@echo "Docs: README.md · $(CLI) --help"

# --- pipeline ---
ingest:
	$(INGEST_ENV) $(CLI) ingest $(INGEST_OPTS)

audit:
	$(PY) scripts/test_wiki_compliance.py
	$(PY) scripts/audit_wiki.py
ifdef LINT
	$(LLM_ENV) $(CLI) lint $(CLI_PROVIDER_ARG)
endif

progress:
	$(CLI) progress

register-reference:
	$(CLI) register-reference

wiki-synthesize:
	$(LLM_ENV) $(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) $(WIKI_SYNTH_OPTS)

wiki-synthesize-apple-notes:
	$(LLM_ENV) $(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) --folder origin-apple-notes $(WIKI_SYNTH_OPTS)

wiki-synth-status:
	$(CLI) progress --wiki-synth-only $(if $(FOLDER),--folder $(FOLDER),)

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
	$(PY) scripts/extract_twitter_raw.py

test:
	@set -- scripts/test_*.py; \
	if [ ! -e "$$1" ]; then echo "No test files found."; exit 0; fi; \
	for f in "$$@"; do $(PY) "$$f" || exit 1; done
