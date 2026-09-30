"""Tests for trace full-paragraph Provenance enforcement."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from trace_engine import (
    build_full_provenance_md,
    enforce_full_provenance,
    extract_cited_para_ids,
    strip_provenance_section,
)


class ProvenanceEnforceTests(unittest.TestCase):
    def test_extract_cited_ids(self) -> None:
        answer = (
            "See (Source: [[raw/_posts/diary/x.md]] · #p1333 · L1–L2\n"
            "> short)\n"
            "Also raw/_posts/a.md#p2 and [[raw/_posts/diary/x.md]] · #p1333 again."
        )
        self.assertEqual(
            extract_cited_para_ids(answer),
            [
                "raw/_posts/diary/x.md#p1333",
                "raw/_posts/a.md#p2",
            ],
        )

    def test_strip_provenance(self) -> None:
        answer = "# q\n\n## Answer\n\nok\n\n## Provenance\n\n- old\n\n## Other\n\nx\n"
        # Provenance is last-ish; strip until next ## or end — ## Other stays
        out = strip_provenance_section(answer)
        self.assertIn("## Answer", out)
        self.assertNotIn("## Provenance", out)
        self.assertIn("## Other", out)

    def test_enforce_replaces_with_full_text(self) -> None:
        answer = (
            "# q\n\n## Answer\n\n"
            "- point (Source: [[raw/_posts/diary/x.md]] · #p1333 · L3753–L3754\n"
            "> truncated)\n\n"
            "## Provenance\n\n"
            "- [[raw/_posts/diary/x.md]] · #p1333 · L3753–L3754\n"
            "  > truncated only\n"
        )
        candidates = [
            {
                "id": "raw/_posts/diary/x.md#p1333",
                "path": "raw/_posts/diary/x.md",
                "para": 1333,
                "start_line": 3753,
                "end_line": 3754,
                "text": (
                    "-   **know and build on your core competencies**\n"
                    "                -   build on them, invest in them, "
                    "**nurture them**, **make them more robust**"
                ),
            }
        ]
        out = enforce_full_provenance(answer, index=None, candidates=candidates)
        self.assertIn("## Provenance", out)
        self.assertIn("know and build on your core competencies", out)
        self.assertIn("make them more robust", out)
        self.assertNotIn("truncated only", out)

    def test_build_provenance_missing(self) -> None:
        md = build_full_provenance_md(
            ["raw/missing.md#p1"], index=None, candidates=[]
        )
        self.assertIn("not found", md)


if __name__ == "__main__":
    unittest.main()
