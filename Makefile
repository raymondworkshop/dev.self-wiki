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
	@echo "  make trace Q=\"what are my core values?\"  # raw-only + cites (default gpt)"
	@echo "  make trace Q=\"什麼是自由？\" raw/_posts/2026-03-01-a-free-man.md  # one note"
	@echo "  make trace-index [FORCE=1]   # rebuild log/trace-index.json"
	@echo "  make trace-serve [PORT=8791] # foreground HTTP (dev)"
	@echo "  make trace-start | stop | restart | logs  # launchd daemon :8791"
	@echo "  TRACE_LLM_MODEL=mlx make trace Q=...   # local privacy instead of gpt"
	@echo "  make audit LINT=1"
	@echo "  make agents            # discover → gap → evolution"
	@echo "  make reflect           # agents + ingest + audit LINT=1"
	@echo "  make site                  # dist/ is http://127.0.0.1:$(TRACE_PORT)/  Trace is /trace/index.html"
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

# gpt by default (faster on long packs); privacy: TRACE_LLM_MODEL=mlx make trace …
TRACE_LLM_MODEL ?= gpt

# `make trace Q="..." raw/_posts/note.md` — the path is the note scope, not a target.
ifeq ($(firstword $(MAKECMDGOALS)),trace)
  TRACE_PATH := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(strip $(TRACE_PATH)),)
    $(eval $(TRACE_PATH):;@:)
  endif
endif
TRACE_SCOPE := $(if $(SCOPE),$(SCOPE),$(TRACE_PATH))

trace:
ifdef Q
	$(LLM_ENV) TRACE_LLM_MODEL=$(TRACE_LLM_MODEL) $(CLI) trace "$(Q)" $(CLI_PROVIDER_ARG) \
	  $(if $(TRACE_SCOPE),--scope "$(TRACE_SCOPE)") \
	  $(if $(DEBUG),--debug-retrieval) $(if $(FORCE),--force-index)
else
	@read -p "trace: " q; $(LLM_ENV) TRACE_LLM_MODEL=$(TRACE_LLM_MODEL) $(CLI) trace "$$q" $(CLI_PROVIDER_ARG) $(if $(TRACE_SCOPE),--scope "$(TRACE_SCOPE)")
endif

TRACE_HOST ?= 0.0.0.0
TRACE_PORT ?= 8791
# Skip vault rescan for this many seconds after a warm ensure_index (hot /ask path).
export TRACE_INDEX_TRUST_SECONDS ?= 180
# Evidence pack size for corpus-wide asks (concept Qs can raise: TRACE_TOP_K=48).
export TRACE_TOP_K ?= 32
# Corpus-wide: ±N paragraphs around each of the top keyword seeds.
export TRACE_NEIGHBOR_RADIUS ?= 1
export TRACE_NEIGHBOR_SEEDS ?= 16
# Soft per-file caps by source tier (corpus-wide mode).
export TRACE_MAX_PER_POST ?= 10
export TRACE_MAX_PER_NOTES ?= 4
export TRACE_MAX_PER_TWITTER ?= 2
# Smaller precise pack when SCOPE=… / UI scope / @file (single-doc mode).
export TRACE_SCOPE_TOP_K ?= 16

TRACE_PLIST_SRC := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/launchd/com.zhaowenlong.self-wiki-trace.plist
TRACE_PLIST := $(HOME)/Library/LaunchAgents/com.zhaowenlong.self-wiki-trace.plist
TRACE_LABEL := com.zhaowenlong.self-wiki-trace

trace-serve:
	$(LLM_ENV) TRACE_LLM_MODEL=$(TRACE_LLM_MODEL) \
	  TRACE_INDEX_TRUST_SECONDS=$(TRACE_INDEX_TRUST_SECONDS) \
	  TRACE_TOP_K=$(TRACE_TOP_K) TRACE_SCOPE_TOP_K=$(TRACE_SCOPE_TOP_K) \
	  TRACE_NEIGHBOR_RADIUS=$(TRACE_NEIGHBOR_RADIUS) TRACE_NEIGHBOR_SEEDS=$(TRACE_NEIGHBOR_SEEDS) \
	  TRACE_MAX_PER_POST=$(TRACE_MAX_PER_POST) TRACE_MAX_PER_NOTES=$(TRACE_MAX_PER_NOTES) \
	  TRACE_MAX_PER_TWITTER=$(TRACE_MAX_PER_TWITTER) \
	  $(PY) scripts/trace_server.py --host $(TRACE_HOST) --port $(TRACE_PORT)

trace-start trace-restart:
	@mkdir -p "$(dir $(TRACE_PLIST_SRC))"
	cp "$(TRACE_PLIST_SRC)" "$(TRACE_PLIST)"
	launchctl unload "$(TRACE_PLIST)" 2>/dev/null || true
	launchctl load "$(TRACE_PLIST)"
	launchctl kickstart -k "gui/$$(id -u)/$(TRACE_LABEL)"
	@echo "site http://0.0.0.0:$(TRACE_PORT)/  trace http://0.0.0.0:$(TRACE_PORT)/trace/index.html"
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
	@echo "Site:  http://127.0.0.1:$(TRACE_PORT)/"
	@echo "Memex: http://127.0.0.1:$(TRACE_PORT)/memex/index.html"
	@echo "Trace: http://127.0.0.1:$(TRACE_PORT)/trace/index.html"
	@echo "Served by the trace daemon (make trace-start)."

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
