# Higher-level analysis and reporting flows

.PHONY: discover gap evolution agents cycle

discover gap evolution:
	$(LLM_ENV) $(CLI) $@

agents: discover gap evolution

cycle: agents post-ingest audit LINT=1
