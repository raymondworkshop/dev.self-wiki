# Shared variables and argument packs

PY  := .selfwikienv/bin/python3
CLI := $(PY) scripts/cli.py

## LLM provider (single knob for sync / compress / wiki / query / reflect / lint)
LLM_PROVIDER ?= mlx
LLM_ENV := ALLOW_PYTHON_LLM=1 ALLOW_LOCAL_LLM=1 LLM_PROVIDER=$(LLM_PROVIDER)
CLI_PROVIDER_ARG := --provider $(LLM_PROVIDER)

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

DOCTOR_ARGS := $(if $(RAW),--raw $(RAW),) $(CLI_PROVIDER_ARG)
