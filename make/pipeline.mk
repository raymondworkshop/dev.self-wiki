# Core pipeline and deterministic trust layer

.PHONY: post-ingest audit progress register-reference compress sync fix-provenance \
	wiki-synthesize wiki-synthesize-apple-notes wiki-synth-status

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

sync:
	$(LLM_ENV) WIKI_SYNTH=0 SYNC_SKIP_POST_INGEST=1 $(SYNC_BATCH_ENV) \
		$(CLI) sync $(CLI_PROVIDER_ARG) && \
	$(LLM_ENV) $(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) $(WIKI_SYNTH_OPTS) --post-ingest

fix-provenance:
	$(PY) scripts/fix_provenance_links.py $(if $(DRY),--dry-run)
	$(if $(DRY),,$(CLI) post-ingest)

wiki-synth-status:
	$(CLI) progress --wiki-synth-only $(if $(FOLDER),--folder $(FOLDER),)

wiki-synthesize-apple-notes:
	$(LLM_ENV) $(CLI) wiki-synthesize $(CLI_PROVIDER_ARG) --folder origin-apple-notes $(WIKI_SYNTH_OPTS)
