# Self Wiki Base Automation

PYTHON = .selfwikienv/bin/python3

.PHONY: help sync audit push

help:
	@echo "self-wiki Commands:"
	@echo "  make sync    - Get the prompt to synchronize wiki/ from raw/ sources"
	@echo "  make audit   - Get the prompt to perform a wiki lint/audit"
	@echo "  make backliner - Run the backliner script"
	@echo "  make hub     - Update all hub pages"
	@echo "  make test    - Test wiki compliance"
	@echo "  make query     - Query your Second Brain"
	@echo "  make push      - Commit and push all changes"

sync:
	$(PYTHON) scripts/sync_wiki.py

audit:
	$(PYTHON) scripts/audit_wiki.py


backliner:
	$(PYTHON) scripts/backliner.py

hub: # update all hub pages
	$(PYTHON) scripts/sync_all_hubs.py

test:
	$(PYTHON) scripts/test_wiki_compliance.py

query:
	@read -p "Query your Second Brain: " q; $(PYTHON) scripts/query_wiki.py "$$q"

push:
	git add .
	git commit -m "self-wiki update: $$(date +'%Y-%m-%d')"
	git push
