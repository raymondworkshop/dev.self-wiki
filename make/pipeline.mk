# Core pipeline and deterministic trust layer

.PHONY: post-ingest audit progress register-reference compress sync \
	wiki-synthesize wiki-synthesize-apple-notes wiki-synth-status

post-ingest:
	$(CLI) post-ingest

audit:
	$(PY) scripts/test_wiki_compliance.py
	$(PY) scripts/audit_wiki.py
ifdef LINT
	$(QUERY_ENV) $(CLI) lint
endif

progress:
	$(CLI) progress

register-reference:
	$(CLI) register-reference

compress:
	$(LLM_ENV) COMPRESS_LLM_PROVIDER=$(COMPRESS_PROVIDER) \
		$(CLI) compress $(COMPRESS_OPTS)

wiki-synthesize:
	$(LLM_ENV) WIKI_SYNTH_LLM_PROVIDER=$(WIKI_PROVIDER) \
		$(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) $(WIKI_SYNTH_OPTS)

sync:
	$(LLM_ENV) COMPRESS_LLM_PROVIDER=$(COMPRESS_PROVIDER) \
		WIKI_SYNTH=0 \
		SYNC_SKIP_POST_INGEST=1 \
		$(SYNC_BATCH_ENV) \
		$(CLI) sync $(CLI_PROVIDER_ARG) && \
	$(LLM_ENV) WIKI_SYNTH_LLM_PROVIDER=$(WIKI_PROVIDER) \
		$(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) $(WIKI_SYNTH_OPTS) --post-ingest

wiki-synth-status:
	$(CLI) progress --wiki-synth-only $(if $(FOLDER),--folder $(FOLDER),)

wiki-synthesize-apple-notes:
	$(LLM_ENV) WIKI_SYNTH_LLM_PROVIDER=$(WIKI_PROVIDER) \
		$(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) --folder origin-apple-notes $(WIKI_SYNTH_OPTS)
