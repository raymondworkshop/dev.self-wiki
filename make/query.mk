# Query, promotion, diagnostics and tests

.PHONY: promote query query-web doctor-config test

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

doctor-config:
	$(LLM_ENV) $(CLI) doctor-config $(DOCTOR_ARGS)

test:
	@set -- scripts/test_*.py; \
	if [ ! -e "$$1" ]; then echo "No test files found."; exit 0; fi; \
	for f in "$$@"; do $(PY) "$$f" || exit 1; done
