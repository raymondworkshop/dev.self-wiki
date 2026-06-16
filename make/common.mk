# Shared variables and argument packs

PY  := .selfwikienv/bin/python3
CLI := $(PY) scripts/cli.py

## Environment wrappers
LLM_ENV   := ALLOW_PYTHON_LLM=1
QUERY_ENV := QUERY_LLM_PROVIDER=$(or $(QUERY_LLM_PROVIDER),gemini)

## Stage provider resolution (legacy INGEST_LLM_PROVIDER kept as fallback)
COMPRESS_PROVIDER := $(or $(COMPRESS_LLM_PROVIDER),$(INGEST_LLM_PROVIDER),$(QUERY_LLM_PROVIDER),gemini)
WIKI_PROVIDER := $(or $(WIKI_SYNTH_LLM_PROVIDER),$(INGEST_LLM_PROVIDER),$(QUERY_LLM_PROVIDER),gemini)

## Shared CLI args
CLI_PROVIDER_ARG := $(if $(PROVIDER),--provider $(PROVIDER),)
DOCTOR_ARGS := $(if $(RAW),--raw $(RAW),) $(CLI_PROVIDER_ARG)

## Stage option packs
COMPRESS_OPTS := $(if $(LIMIT),--limit $(LIMIT)) $(if $(FORCE),--force) \
	$(if $(FOLDER),--folder $(FOLDER)) $(if $(POST_INGEST),--post-ingest)

WIKI_SYNTH_OPTS := $(if $(LIMIT),--limit $(LIMIT)) $(if $(FORCE),--force) \
	$(if $(FOLDER),--folder $(FOLDER)) $(if $(WAVE),--wave $(WAVE)) \
	$(if $(POST_INGEST),--post-ingest)

SYNC_BATCH_ENV := POSTS_BATCH=$(or $(POSTS_BATCH),0) \
	MAX_INGEST_BATCH_TOKENS=$(or $(MAX_INGEST_BATCH_TOKENS),150000) \
	MAX_INGEST_BATCH_FILES=$(or $(MAX_INGEST_BATCH_FILES),8) \
	POSTS_BATCH_MAX_LINES=$(or $(POSTS_BATCH_MAX_LINES),400)
