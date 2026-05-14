# Self Wiki Base Automation

.PHONY: help sync audit push

help:
	@echo "self-wiki Commands:"
	@echo "  make sync    - Get the prompt to synchronize wiki/ from raw/ sources"
	@echo "  make audit   - Get the prompt to perform a wiki lint/audit"
	@echo "  make push    - Commit and push all changes"

sync:
	@echo "update wiki/ based on raw/ and GEMINI.md"

audit:
	python3 scripts/audit_wiki.py

report:

push:
	git add .
	git commit -m "self-wiki update: $$(date +'%Y-%m-%d')"
	git push