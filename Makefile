# Self Wiki Base Automation

.PHONY: help sync audit push

help:
	@echo "self-wiki Commands:"
	@echo "  make sync    - Get the prompt to synchronize wiki/ from raw/ sources"
	@echo "  make audit   - Get the prompt to perform a wiki lint/audit"
	@echo "  make backliner - Run the backliner script"
	@echo "  make query     - Query your Second Brain"
	@echo "  make push      - Commit and push all changes"

sync:
	python3 scripts/sync_wiki.py

audit:
	python3 scripts/audit_wiki.py


backliner:
	python3 scripts/backliner.py

test:
	python3 scripts/test_wiki_compliance.py

query:
	@read -p "Query your Second Brain: " q; python3 scripts/query_wiki.py "$$q"

push:
	git add .
	git commit -m "self-wiki update: $$(date +'%Y-%m-%d')"
	git push
