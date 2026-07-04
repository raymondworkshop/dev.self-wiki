# Higher-level analysis and reporting flows

.PHONY: discover gap evolution agents reflect

discover gap evolution:
	$(LLM_ENV) $(CLI) $@ $(CLI_PROVIDER_ARG)

agents: discover gap evolution

reflect: agents post-ingest audit LINT=1
