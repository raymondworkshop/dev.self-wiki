# Self Wiki — Python CLI

.DEFAULT_GOAL := help

PY  := .selfwikienv/bin/python3
CLI := $(PY) scripts/cli.py

LLM_PROVIDER ?= mlx
LLM_ENV := ALLOW_PYTHON_LLM=1 ALLOW_LOCAL_LLM=1 LLM_PROVIDER=$(LLM_PROVIDER)
CLI_PROVIDER_ARG := --provider $(LLM_PROVIDER)

COMPRESS_OPTS := $(if $(LIMIT),--limit $(LIMIT)) $(if $(FORCE),--force) \
	$(if $(FOLDER),--folder $(FOLDER)) $(if $(POST_INGEST),--post-ingest)
WIKI_SYNTH_OPTS := $(if $(LIMIT),--limit $(LIMIT)) $(if $(FORCE),--force) \
	$(if $(FOLDER),--folder $(FOLDER)) $(if $(WAVE),--wave $(WAVE)) \
	$(if $(POST_INGEST),--post-ingest)
SYNC_BATCH_ENV := POSTS_BATCH=$(or $(POSTS_BATCH),0) \
	MAX_INGEST_BATCH_TOKENS=$(or $(MAX_INGEST_BATCH_TOKENS),150000) \
	MAX_INGEST_BATCH_FILES=$(or $(MAX_INGEST_BATCH_FILES),8) \
	POSTS_BATCH_MAX_LINES=$(or $(POSTS_BATCH_MAX_LINES),400)
DOCTOR_ARGS := $(if $(RAW),--raw $(RAW),) $(CLI_PROVIDER_ARG)

.PHONY: help post-ingest audit progress register-reference compress sync \
	fix-provenance wiki-synthesize wiki-synthesize-apple-notes wiki-synth-status \
	discover gap evolution agents reflect promote query query-web test \
	doctor-config publish

help:
	@echo "Daily:  sync · query · audit · reflect · publish · query-web"
	@echo "Pipeline:  compress · wiki-synthesize · post-ingest · progress · fix-provenance"
	@echo "Agents:  discover · gap · evolution · agents"
	@echo "Other:  promote · register-reference · test · doctor-config"
	@echo ""
	@echo "Examples:"
	@echo "  make sync"
	@echo "  make query Q=\"what are my values?\""
	@echo "  make audit LINT=1"
	@echo "  make publish [BUILD_ONLY=1]"
	@echo ""
	@echo "Docs: README.md · $(CLI) --help"

# --- pipeline ---
post-ingest:
	$(CLI) post-ingest

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

compress:
	$(LLM_ENV) $(CLI) compress $(CLI_PROVIDER_ARG) $(COMPRESS_OPTS)

wiki-synthesize:
	$(LLM_ENV) $(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) $(WIKI_SYNTH_OPTS)

wiki-synthesize-apple-notes:
	$(LLM_ENV) $(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) --folder origin-apple-notes $(WIKI_SYNTH_OPTS)

wiki-synth-status:
	$(CLI) progress --wiki-synth-only $(if $(FOLDER),--folder $(FOLDER),)

sync:
	$(LLM_ENV) WIKI_SYNTH=0 SYNC_SKIP_POST_INGEST=1 $(SYNC_BATCH_ENV) \
		$(CLI) sync $(CLI_PROVIDER_ARG) && \
	$(LLM_ENV) $(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) $(WIKI_SYNTH_OPTS) --post-ingest

fix-provenance:
	$(PY) scripts/fix_provenance_links.py $(if $(DRY),--dry-run)
	$(if $(DRY),,$(CLI) post-ingest)

# --- agents ---
discover gap evolution:
	$(LLM_ENV) $(CLI) $@ $(CLI_PROVIDER_ARG)

agents: discover gap evolution

reflect: agents post-ingest audit LINT=1

# --- query & publish ---
promote:
	$(CLI) promote --file $(FILE) --target $(TARGET) $(if $(CONFIRM),--confirm)

query:
ifdef Q
	$(LLM_ENV) $(CLI) query "$(Q)" $(CLI_PROVIDER_ARG)
else
	@read -p "Query: " q; $(LLM_ENV) $(CLI) query "$$q" $(CLI_PROVIDER_ARG)
endif

query-web:
	$(PY) scripts/query_server.py

publish:
	$(PY) scripts/publish_wiki.py \
	  $(if $(BUILD_ONLY),,--deploy) \
	  $(if $(PUBLISH_DIR),--out $(PUBLISH_DIR),) \
	  $(if $(CLOUDFLARE_PAGES_PROJECT),--project $(CLOUDFLARE_PAGES_PROJECT),)

doctor-config:
	$(LLM_ENV) $(CLI) doctor-config $(DOCTOR_ARGS)

test:
	@set -- scripts/test_*.py; \
	if [ ! -e "$$1" ]; then echo "No test files found."; exit 0; fi; \
	for f in "$$@"; do $(PY) "$$f" || exit 1; done
