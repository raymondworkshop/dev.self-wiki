import json
import os
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

- 2026-01-01: Distilled from raw source [[raw/origin-apple-notes/test.md]].
- init

## Backlinks

- **Contradicts**: none

## Sources

- [[raw/origin-apple-notes/test.md]]
"""

L1_PRINCIPLE_PAGE = """---
title: L1 Tagged Principle
level: 1
confidence: 0.95
tags: [type/principle]
last_updated: 2026-01-01
---

> Should not enter twin catalog (Level 1).

## Evolution

## Backlinks

## Sources
"""

SHIFT_PAGE = """---
title: Test Shift
level: 1
tags: [type/shift]
last_updated: 2026-06-01
---

> A recent cognitive shift from query promotion.

## Evolution

- 2026-06-01: Promoted query output into this page (type/shift).

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

- [[raw/origin-apple-notes/tension.md]]
"""


class BuildTwinProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wiki = self.root / "self-wiki" / "wiki"
        self.wiki.mkdir(parents=True)
        self.profile = self.root / "twin" / "PROFILE.md"
        self.principles_json = self.root / "twin" / "principles.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_profile_markdown_includes_sections(self):
        (self.wiki / "principle.md").write_text(PRINCIPLE_PAGE, encoding="utf-8")
        (self.wiki / "l1.md").write_text(L1_PRINCIPLE_PAGE, encoding="utf-8")
        (self.wiki / "shift.md").write_text(SHIFT_PAGE, encoding="utf-8")
        (self.wiki / "tension.md").write_text(TENSION_PAGE, encoding="utf-8")

        with (
            patch.object(btp, "WIKI_DIR", self.wiki),
            patch.object(btp, "WORKSPACE_PATH", self.root),
            patch.object(btp, "TWIN_PRINCIPLES_JSON", self.principles_json),
        ):
            text = btp.build_profile_markdown(
                built_at=datetime(2026, 6, 2, 12, 0, 0)
            )

        self.assertIn("## Operating principles", text)
        self.assertIn("principle.md", text)
        self.assertIn("compressed principle for testing", text)
        self.assertNotIn("L1 Tagged Principle", text)
        self.assertIn("## Recent shifts", text)
        self.assertIn("shift.md", text)
        self.assertIn("cognitive shift from query", text)
        self.assertIn("## Active tensions", text)
        self.assertIn("speed vs depth", text)
        self.assertIn("## Recent evolution", text)
        self.assertIn("Promoted query output", text)
        self.assertIn("principle_count: 2", text)
        self.assertIn("principles.json", text)

    def test_build_twin_profile_writes_profile_and_json(self):
        (self.wiki / "principle.md").write_text(PRINCIPLE_PAGE, encoding="utf-8")

        patches = (
            patch.object(btp, "WIKI_DIR", self.wiki),
            patch.object(btp, "WORKSPACE_PATH", self.root),
            patch.object(btp, "TWIN_PROFILE", self.profile),
            patch.object(btp, "TWIN_PRINCIPLES_JSON", self.principles_json),
        )
        with patches[0], patches[1], patches[2], patches[3]:
            path = btp.build_twin_profile()

        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("Digital Twin Profile", content)
        self.assertIn("compressed principle for testing", content)

        data = json.loads(self.principles_json.read_text(encoding="utf-8"))
        self.assertEqual(data["principle_count"], 1)
        self.assertEqual(len(data["principles"]), 1)
        self.assertEqual(data["principles"][0]["title"], "Test Principle")

    def test_profile_caps_principles_when_env_set(self):
        for i in range(5):
            (self.wiki / f"p{i}.md").write_text(
                PRINCIPLE_PAGE.replace("Test Principle", f"Principle {i}").replace(
                    "0.9", f"0.{9 - i % 3}"
                ),
                encoding="utf-8",
            )

        env = {**os.environ, "TWIN_PROFILE_MAX_PRINCIPLES": "2"}
        with (
            patch.object(btp, "WIKI_DIR", self.wiki),
            patch.object(btp, "WORKSPACE_PATH", self.root),
            patch.object(btp, "TWIN_PRINCIPLES_JSON", self.principles_json),
            patch.dict(os.environ, env, clear=False),
        ):
            text = btp.build_profile_markdown(built_at=datetime(2026, 6, 2))

        self.assertIn("principle_count: 5", text)
        self.assertIn("principle_count_shown: 2", text)
        self.assertIn("Showing top 2", text)


if __name__ == "__main__":
    unittest.main()
