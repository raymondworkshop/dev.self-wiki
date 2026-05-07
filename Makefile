# Self Wiki Base Automation

.PHONY: help sync audit push

help:
	@echo "rbrain Commands:"
	@echo "  make sync    - Get the prompt to synchronize wiki/ from raw/ sources"
	@echo "  make audit   - Get the prompt to perform a wiki lint/audit"
	@echo "  make push    - Commit and push all changes"

sync:
	@echo "update wiki/ based on raw/ and GEMINI.md"

audit:
	@echo "Review the entire wiki/ directory. Complete the audit defined in GEMINI.md."

push:
	git add .
	git commit -m "rbrain update: $$(date +'%Y-%m-%d')"
	git push