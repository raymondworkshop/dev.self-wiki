import os
import unittest
from pathlib import Path

import yaml
from config import WIKI_DIR
from models import WikiPage


class TestWikiModels(unittest.TestCase):
    def setUp(self):
        self.test_file = WIKI_DIR / "Test_Topic.md"
        if self.test_file.exists():
            self.test_file.unlink()

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()

    def test_page_lifecycle(self):
        """Test creating, saving, and loading a WikiPage."""
        page = WikiPage.create_new("Test Topic", level=2)
        page.summary = "This is a socratic summary. It should be two sentences long."
        page.body = "This is the main content of the test page."
        page.evolution = "- Added for testing."
        page.sources = ["raw/test-source.md"]
        page.front_matter["tags"] = ["test", "type/principle"]
        page.save()

        # Reload
        reloaded = WikiPage(self.test_file)
        self.assertEqual(reloaded.front_matter["title"], "Test Topic")
        self.assertEqual(reloaded.front_matter["level"], 2)
        self.assertEqual(
            reloaded.summary,
            "This is a socratic summary. It should be two sentences long.",
        )
        self.assertIn("raw/test-source.md", reloaded.sources)
        self.assertIn("Evolution", reloaded.content)
        self.assertIn("Backlinks", reloaded.content)


class TestTraceability(unittest.TestCase):
    def test_level_2_traceability(self):
        """Verify all Level 2 pages have at least one source."""
        wiki_files = list(WIKI_DIR.rglob("*.md"))
        for f in wiki_files:
            if f.name in ["INDEX.md", "audit.md"] or "-Hub" in f.name:
                continue

            page = WikiPage(f)
            if page.front_matter.get("level") == 2:
                self.assertTrue(
                    len(page.sources) > 0,
                    f"Level 2 Principle '{f.name}' must have at least one source link.",
                )


if __name__ == "__main__":
    unittest.main()
