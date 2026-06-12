import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_twin_profile as tc


class TwinProfileExcerptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.profile = self.root / "twin" / "PROFILE.md"
        self.principles_json = self.root / "twin" / "principles.json"
        self.profile.parent.mkdir(parents=True)

        self.profile.write_text(
            """---
title: Digital Twin Profile
principle_count: 3
---

> Snapshot.

## Operating principles

- [[wiki/a.md]] (L2, conf 0.95) — Alpha principle.

## Active tensions

- [[wiki/t.md]] → speed vs depth

## Recent shifts

- [[wiki/s.md]] — A recent shift.

## Recent evolution

- 2026-06-01 — [[wiki/s.md]]: Promoted query output (type/shift).

## Compiled

- 2026-06-12: test
""",
            encoding="utf-8",
        )

        payload = {
            "principle_count": 3,
            "principles": [
                {
                    "title": "Personality Trait",
                    "rel": "self-wiki/wiki/personality.md",
                    "level": 2,
                    "confidence": 0.9,
                    "summary": "Core personality and character patterns.",
                    "last_updated": "2026-06-01",
                    "tags": ["type/principle"],
                },
                {
                    "title": "Tax Planning",
                    "rel": "self-wiki/wiki/tax.md",
                    "level": 2,
                    "confidence": 1.0,
                    "summary": "Legal tax planning for wealth.",
                    "last_updated": "2026-06-01",
                    "tags": ["type/principle"],
                },
                {
                    "title": "Trust",
                    "rel": "self-wiki/wiki/trust.md",
                    "level": 2,
                    "confidence": 0.95,
                    "summary": "Honesty in all dealings.",
                    "last_updated": "2026-06-01",
                    "tags": ["type/principle"],
                },
            ],
        }
        self.principles_json.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _patches(self):
        return (
            patch.object(tc, "WORKSPACE_PATH", self.root),
            patch.object(tc, "TWIN_PROFILE", self.profile),
            patch.object(tc, "TWIN_PRINCIPLES_JSON", self.principles_json),
        )

    def test_score_principle_prefers_matching_terms(self):
        personality = {
            "title": "Personality Trait",
            "summary": "character and self-awareness",
            "rel": "wiki/personality.md",
            "level": 2,
            "confidence": 0.9,
        }
        tax = {
            "title": "Tax",
            "summary": "wealth management",
            "rel": "wiki/tax.md",
            "level": 2,
            "confidence": 1.0,
        }
        terms = ["personality", "character", "性格"]
        self.assertGreater(
            tc.score_principle(personality, "我的性格", terms),
            tc.score_principle(tax, "我的性格", terms),
        )

    def test_profile_excerpt_includes_relevant_principles_and_sections(self):
        with self._patches()[0], self._patches()[1], self._patches()[2]:
            text = tc.profile_excerpt_for_query(
                "我的性格是什么特点",
                ["personality", "character", "性格"],
                top_k=1,
            )

        self.assertIn("## Relevant operating principles", text)
        self.assertIn("personality.md", text)
        self.assertIn("## Active tensions", text)
        self.assertIn("speed vs depth", text)
        self.assertIn("## Recent shifts", text)
        self.assertIn("A recent shift", text)
        self.assertIn("## Recent evolution", text)
        self.assertIn("Promoted query output", text)
        self.assertNotIn("tax.md", text)

    def test_lint_profile_summary_is_bounded(self):
        with self._patches()[0], self._patches()[1], self._patches()[2]:
            text = tc.lint_profile_summary(max_chars=1500)

        self.assertIn("principle_count: 3", text)
        self.assertIn("## Active tensions", text)
        self.assertLessEqual(len(text), 1500)


if __name__ == "__main__":
    unittest.main()
