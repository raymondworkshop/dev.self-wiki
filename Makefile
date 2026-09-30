# Self Wiki — Python CLI

.DEFAULT_GOAL := help

PY  := .selfwikienv/bin/python3
CLI := $(PY) scripts/cli.py

LLM_PROVIDER ?= local-gateway
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
	fix-provenance fix-obsidian-md wiki-synthesize wiki-synthesize-apple-notes wiki-synth-status \
	discover gap evolution agents reflect promote query trace trace-index trace-serve \
	trace-start trace-stop trace-restart trace-logs \
	rdatabase rdatabase-index rdatabase-serve test \
	doctor-config incubate-themes publish site

help:
	@echo "Daily:  sync · ingest · site · publish · query · trace · audit · reflect"
	@echo "Pipeline:  wiki-synthesize · ingest · progress · fix-provenance "
	@echo "Memex:  make memex CMD=\"stats|missing|backlinks PAGE\""
	@echo "Agents:  discover · gap · evolution · agents"
	@echo "Other:  promote · register-reference · test · doctor-config · incubate-themes"
	@echo ""
	@echo "Examples:"
	@echo "  make sync              # changed raw → wiki-synthesize, then ingest"
	@echo "  make sync SKIP_INGEST=1  # wiki-synthesize only, skip ingest"
	@echo "  make ingest [FAST=1]   # memex · index · twin (no LLM)"
	@echo "  make query Q=\"what are my values?\"   # wiki Socratic mirror"
	@echo "  make trace Q=\"what are my core values?\"  # raw-only + cites (default mlx)"
	@echo "  make trace Q=\"什麼是自由？\" SCOPE=a-free-man  # answer from one note only"
	@echo "  make trace-index [FORCE=1]   # rebuild log/trace-index.json"
	@echo "  make trace-serve [PORT=8791] # foreground HTTP (dev)"
	@echo "  make trace-start | stop | restart | logs  # launchd daemon :8791"
	@echo "  TRACE_LLM_MODEL=gpt make trace Q=...   # use cloud instead of mlx"
	@echo "  make audit LINT=1"
	@echo "  make agents            # discover → gap → evolution"
	@echo "  make reflect           # agents + ingest + audit LINT=1"
	@echo "  make site [PORT=8787]     # serve dist/ locally (build first: ingest + publish BUILD_ONLY=1)"
	@echo "  make publish [BUILD_ONLY=1]"
	@echo ""
	@echo "trace knobs: TRACE_TOP_K=$(TRACE_TOP_K)  TRACE_MAX_PER_POST=$(TRACE_MAX_PER_POST)"
	@echo "             TRACE_MAX_PER_NOTES=$(TRACE_MAX_PER_NOTES)  TRACE_MAX_PER_TWITTER=$(TRACE_MAX_PER_TWITTER)"
	@echo "             TRACE_SCOPE_TOP_K=$(TRACE_SCOPE_TOP_K)  (single-doc pack size)"
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

fix-obsidian-md:
	$(PY) scripts/md_obsidian_sanitize.py $(if $(PATHS),$(PATHS),self-wiki/wiki)

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

trace-index:
	$(CLI) trace-index $(if $(FORCE),--force)

# Local mlx by default (raw cites stay private); override: TRACE_LLM_MODEL=gpt make trace …
TRACE_LLM_MODEL ?= mlx

trace:
ifdef Q
	$(LLM_ENV) TRACE_LLM_MODEL=$(TRACE_LLM_MODEL) $(CLI) trace "$(Q)" $(CLI_PROVIDER_ARG) \
	  $(if $(SCOPE),--scope "$(SCOPE)") \
	  $(if $(DEBUG),--debug-retrieval) $(if $(FORCE),--force-index)
else
	@read -p "trace: " q; $(LLM_ENV) TRACE_LLM_MODEL=$(TRACE_LLM_MODEL) $(CLI) trace "$$q" $(CLI_PROVIDER_ARG) $(if $(SCOPE),--scope "$(SCOPE)")
endif

TRACE_HOST ?= 0.0.0.0
TRACE_PORT ?= 8791
# Skip vault rescan for this many seconds after a warm ensure_index (hot /ask path).
export TRACE_INDEX_TRUST_SECONDS ?= 180
# Evidence pack size for corpus-wide asks (concept Qs can raise: TRACE_TOP_K=48).
export TRACE_TOP_K ?= 32
# Soft per-file caps by source tier (corpus-wide mode).
export TRACE_MAX_PER_POST ?= 10
export TRACE_MAX_PER_NOTES ?= 4
export TRACE_MAX_PER_TWITTER ?= 2
# Larger pack when SCOPE=… / UI scope / @file (single-doc mode).
export TRACE_SCOPE_TOP_K ?= 64

TRACE_PLIST_SRC := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/launchd/com.zhaowenlong.self-wiki-trace.plist
TRACE_PLIST := $(HOME)/Library/LaunchAgents/com.zhaowenlong.self-wiki-trace.plist
TRACE_LABEL := com.zhaowenlong.self-wiki-trace

trace-serve:
	$(LLM_ENV) TRACE_LLM_MODEL=$(TRACE_LLM_MODEL) \
	  TRACE_INDEX_TRUST_SECONDS=$(TRACE_INDEX_TRUST_SECONDS) \
	  TRACE_TOP_K=$(TRACE_TOP_K) TRACE_SCOPE_TOP_K=$(TRACE_SCOPE_TOP_K) \
	  TRACE_MAX_PER_POST=$(TRACE_MAX_PER_POST) TRACE_MAX_PER_NOTES=$(TRACE_MAX_PER_NOTES) \
	  TRACE_MAX_PER_TWITTER=$(TRACE_MAX_PER_TWITTER) \
	  $(PY) scripts/trace_server.py --host $(TRACE_HOST) --port $(TRACE_PORT)

trace-start trace-restart:
	@mkdir -p "$(dir $(TRACE_PLIST_SRC))"
	cp "$(TRACE_PLIST_SRC)" "$(TRACE_PLIST)"
	launchctl unload "$(TRACE_PLIST)" 2>/dev/null || true
	launchctl load "$(TRACE_PLIST)"
	launchctl kickstart -k "gui/$$(id -u)/$(TRACE_LABEL)"
	@echo "trace daemon on http://0.0.0.0:$(TRACE_PORT)/ (Tailscale: http://100.90.225.26:$(TRACE_PORT)/)"
	@echo "logs: launchd/launchd-trace*.log"

trace-stop:
	launchctl unload "$(TRACE_PLIST)" 2>/dev/null || true
	@echo "trace daemon unloaded"

trace-logs:
	@tail -f launchd/launchd-trace.log launchd/launchd-trace.err.log

# Back-compat aliases (formerly rdatabase)
rdatabase: trace
rdatabase-index: trace-index
rdatabase-serve: trace-serve
rdatabase-start: trace-start
rdatabase-stop: trace-stop
rdatabase-restart: trace-restart
rdatabase-logs: trace-logs

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

incubate-themes:
	$(PY) scripts/incubate_themes.py $(if $(DRY),--dry-run) $(if $(INGEST),--ingest)

extract-twitter:
	$(PY) scripts/extract_twitter_raw.py

test:
	@set -- scripts/test_*.py; \
	if [ ! -e "$$1" ]; then echo "No test files found."; exit 0; fi; \
	for f in "$$@"; do $(PY) "$$f" || exit 1; done
