# Query, promotion, diagnostics and tests

.PHONY: promote query query-web doctor-config test

promote:
	$(CLI) promote --file $(FILE) --target $(TARGET) $(if $(CONFIRM),--confirm)

query:
ifdef Q
	$(QUERY_ENV) $(CLI) query "$(Q)"
else
	@read -p "Query: " q; $(QUERY_ENV) $(CLI) query "$$q"
endif

query-web:
	$(PY) scripts/query_server.py

doctor-config:
	$(CLI) doctor-config $(DOCTOR_ARGS)

test:
	@set -- scripts/test_*.py; \
	if [ ! -e "$$1" ]; then echo "No test files found."; exit 0; fi; \
	for f in "$$@"; do $(PY) "$$f" || exit 1; done
