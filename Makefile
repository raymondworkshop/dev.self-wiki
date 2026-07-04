# Self Wiki — Python CLI

.DEFAULT_GOAL := help

include make/common.mk
include make/pipeline.mk
include make/analysis.mk
include make/query.mk

.PHONY: help post-ingest audit progress \
	register-reference compress sync fix-provenance \
	wiki-synthesize wiki-synthesize-apple-notes wiki-synth-status \
	discover gap evolution agents reflect \
	promote query query-web test doctor-config

help:
	@echo "Essential (daily):"
	@echo "  make sync                 changed raw → compression → wiki + post-ingest"
	@echo "  make fix-provenance       repair malformed wiki source links"
	@echo "  make query [Q=\"...\"]      ask wiki"
	@echo "  make audit [LINT=1]       compliance (+ optional cognitive lint)"
	@echo "  make reflect              periodic: patterns, gaps, belief evolution + audit"
	@echo ""
	@echo "Advanced:"
	@echo "  make post-ingest          backlinks, INDEX, twin"
	@echo "  make progress             pipeline status"
	@echo "  make wiki-synth-status    wiki-synthesize backfill manifest"
	@echo "  make register-reference   twitter catalog (no LLM)"
	@echo "  make compress             raw → compression  (LIMIT FOLDER FORCE POST_INGEST)"
	@echo "  make wiki-synthesize      compression → wiki  (LIMIT FOLDER WAVE POST_INGEST)"
	@echo "  make wiki-synthesize-apple-notes   origin-apple-notes shorthand"
	@echo "  make discover | gap | evolution | agents"
	@echo "  make promote FILE=… TARGET=… [CONFIRM=1]"
	@echo "  make query-web            browser UI"
	@echo "  make doctor-config        resolved provider/model/skill"
	@echo "  make test"
	@echo ""
	@echo "Docs: README.md · design.md · CLI: $(CLI) --help"
