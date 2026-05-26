import hashlib
import json
import logging
import os
import re
from pathlib import Path

from config import GEMINI_CONF, LOG_DIR, RAW_DIR, WIKI_DIR
from models import WikiPage

logger = logging.getLogger(__name__)


class SocraticOrchestrator:
    """Orchestrates the Raw -> Synthesis -> Principle flow."""

    def __init__(self):
        self.cache_path = LOG_DIR / ".sync_cache.json"
        self.cache = self._load_cache()
        self.instructions = GEMINI_CONF.read_text()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text())
            except:
                return {}
        return {}

    def save_cache(self):
        self.cache_path.write_text(json.dumps(self.cache, indent=2))

    def get_changed_files(self):
        changed = []
        for p in RAW_DIR.rglob("*.md", recurse_symlinks=True):
            rel = str(p.relative_to(RAW_DIR))
            curr_hash = hashlib.md5(p.read_bytes()).hexdigest()
            if self.cache.get(rel) != curr_hash:
                changed.append((rel, p, curr_hash))
            else:
                logger.info(f"Skipping unchanged file: {rel}")
        return changed

    def run(self):
        changed = self.get_changed_files()
        if not changed:
            logger.info("Wiki is up to date.")
            return

        logger.info(f"Found {len(changed)} changed files.")
        # In a real run, this would loop and call the distillation skill.
        # For now, we just log.
        for rel, abs_p, h in changed:
            logger.info(f"Ready to distill: {rel}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    orchestrator = SocraticOrchestrator()
    orchestrator.run()
