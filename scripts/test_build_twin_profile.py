import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import build_twin_profile as btp


PRINCIPLE_PAGE = """---
title: Test Principle
level: 2
confidence: 0.9
tags: [type/principle]
last_updated: 2026-01-01
---

> A compressed principle for testing twin profile aggregation.

## Evolution

- init

## Backlinks

- **Contradicts**: none

## Sources

- [[raw/test.md]]
"""

SHIFT_PAGE = """---
title: Test Shift
level: 1
tags: [type/shift]
last_updated: 2026-06-01
---

> A recent cognitive shift from query promotion.

## Evolution

- promoted

## Backlinks

## Sources
"""

TENSION_PAGE = """---
title: Tension Page
level: 2
confidence: 0.8
tags: [type/principle]
---

> Holds an active contradiction edge.

## Evolution

## Backlinks

- **Contradicts**: [[other-page.md]] — speed vs depth

## Sources
"""


class BuildTwinProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wiki = self.root / "self-wiki" / "wiki"
        self.wiki.mkdir(parents=True)
        self.profile = self.root / "twin" / "PROFILE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_profile_markdown_includes_sections(self):
        (self.wiki / "principle.md").write_text(PRINCIPLE_PAGE, encoding="utf-8")
        (self.wiki / "shift.md").write_text(SHIFT_PAGE, encoding="utf-8")
        (self.wiki / "tension.md").write_text(TENSION_PAGE, encoding="utf-8")

        with patch.object(btp, "WIKI_DIR", self.wiki), patch.object(
            btp, "WORKSPACE_PATH", self.root
        ):
            text = btp.build_profile_markdown(
                built_at=datetime(2026, 6, 2, 12, 0, 0)
            )

        self.assertIn("## Operating principles", text)
        self.assertIn("principle.md", text)
        self.assertIn("compressed principle for testing", text)
        self.assertIn("## Recent shifts", text)
        self.assertIn("shift.md", text)
        self.assertIn("cognitive shift from query", text)
        self.assertIn("## Active tensions", text)
        self.assertIn("speed vs depth", text)
        self.assertIn("principle_count: 2", text)

    def test_build_twin_profile_writes_file(self):
        (self.wiki / "principle.md").write_text(PRINCIPLE_PAGE, encoding="utf-8")

        patches = (
            patch.object(btp, "WIKI_DIR", self.wiki),
            patch.object(btp, "WORKSPACE_PATH", self.root),
            patch.object(btp, "TWIN_PROFILE", self.profile),
        )
        with patches[0], patches[1], patches[2]:
            path = btp.build_twin_profile()

        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("Digital Twin Profile", content)
        self.assertIn("compressed principle for testing", content)


if __name__ == "__main__":
    unittest.main()
