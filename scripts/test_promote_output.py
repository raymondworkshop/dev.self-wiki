import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import promote_output as po
from models import WikiPage


WIKI_PAGE = """---
title: Promote Target
level: 2
confidence: 0.85
tags: [type/principle]
last_updated: 2026-01-01
description: Target page for promote tests
---

> Existing principle body.

## Evolution

- seeded

## Backlinks

## Sources

- [[raw/seed.md]]
"""

OUTPUT_MD = """---
title: Test Query Output
---

# Test Query Output

## Answer

Promoted insight: prefer action over rumination when stakes are low.

## Provenance

- [[self-wiki/wiki/note.md]]
"""


class PromoteOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wiki = self.root / "self-wiki" / "wiki"
        self.outputs = self.root / "self-wiki" / "outputs"
        self.wiki.mkdir(parents=True)
        self.outputs.mkdir(parents=True)
        self.wiki_file = self.wiki / "promote-target.md"
        self.wiki_file.write_text(WIKI_PAGE, encoding="utf-8")
        self.output_file = self.outputs / "test-promote.md"
        self.output_file.write_text(OUTPUT_MD, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _title_map(self):
        return {}, {"Promote Target": self.wiki_file}

    def test_dry_run_does_not_modify_wiki(self):
        before = self.wiki_file.read_text(encoding="utf-8")
        with patch.object(po, "WORKSPACE_PATH", self.root), patch.object(
            po, "OUTPUTS_DIR", self.outputs
        ), patch.object(po, "load_existing_themes", return_value=self._title_map()):
            result = po.promote_output(
                str(self.output_file.relative_to(self.root)),
                "Promote Target",
                confirm=False,
            )

        after = self.wiki_file.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertFalse(result.get("applied"))
        self.assertIn("Promoted from query", result["preview"])
        self.assertIn("action over rumination", result["preview"])

    def test_confirm_appends_distillation_and_shift_tag(self):
        rel_out = str(self.output_file.relative_to(self.root))
        with patch.object(po, "WORKSPACE_PATH", self.root), patch.object(
            po, "OUTPUTS_DIR", self.outputs
        ), patch.object(po, "load_existing_themes", return_value=self._title_map()):
            result = po.promote_output(rel_out, "Promote Target", confirm=True)

        self.assertTrue(result.get("applied"))
        content = self.wiki_file.read_text(encoding="utf-8")
        self.assertIn("Promoted from query", content)
        self.assertIn("action over rumination", content)
        page = WikiPage(self.wiki_file)
        self.assertIn("type/shift", page.front_matter.get("tags", []))
        self.assertTrue(any(rel_out in s for s in page.sources))


if __name__ == "__main__":
    unittest.main()
