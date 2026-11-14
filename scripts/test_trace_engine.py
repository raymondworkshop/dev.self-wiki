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
    render_trace_answer,
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
            },
            {
                "id": "raw/_posts/other.md#p2",
                "path": "raw/_posts/other.md",
                "para": 2,
                "start_line": 10,
                "end_line": 11,
                "text": "uncited pack paragraph about freedom",
            },
        ]
        out = enforce_full_provenance(answer, index=None, candidates=candidates)
        self.assertIn("## Provenance", out)
        self.assertIn("know and build on your core competencies", out)
        self.assertIn("make them more robust", out)
        self.assertNotIn("truncated only", out)
        self.assertIn("uncited pack paragraph about freedom", out)
        self.assertIn("Evidence Pack hit (not cited in Answer)", out)

    def test_render_puts_cites_in_sources(self) -> None:
        md = render_trace_answer(
            "什么是自由",
            [
                {
                    "path": "raw/_posts/a.md",
                    "para": 4,
                    "start_line": 40,
                    "end_line": 48,
                    "text": "真正的自由是有信心做自己。",
                    "via": "both",
                    "role": "hit",
                },
                {
                    "path": "raw/_posts/b.md",
                    "para": 2,
                    "start_line": 10,
                    "end_line": 12,
                    "text": "Luck and risk are the same coin.",
                    "via": "vector",
                    "role": "hit",
                },
            ],
            language="Chinese",
        )
        self.assertIn("### a", md)
        cite_a = "[[raw/_posts/a.md]] · #p4 · L40–L48"
        self.assertLess(md.index(cite_a), md.index("> 真正的自由是有信心做自己。"))
        self.assertIn("> 真正的自由是有信心做自己。", md)
        self.assertIn("### b", md)
        cite_b = "[[raw/_posts/b.md]] · #p2 · L10–L12"
        self.assertLess(md.index(cite_b), md.index("> Luck and risk are the same coin."))
        self.assertNotIn("· 向量", md)
        self.assertNotIn("- [[", md)

    def test_passage_stays_verbatim(self) -> None:
        text = "#### 人生的自由\n* **做你能做的**\n    - 剩下的不妨順其自然。"
        md = render_trace_answer(
            "自由",
            [
                {
                    "path": "raw/_posts/note.md",
                    "para": 8,
                    "start_line": 20,
                    "end_line": 24,
                    "text": text,
                    "role": "hit",
                }
            ],
            language="Chinese",
        )
        cite = "[[raw/_posts/note.md]] · #p8 · L20–L24"
        self.assertLess(md.index(cite), md.index("> #### 人生的自由"))
        self.assertIn("> * **做你能做的**", md)
        self.assertIn(">     - 剩下的不妨順其自然。", md)

    def test_build_provenance_missing(self) -> None:
        md = build_full_provenance_md(
            ["raw/missing.md#p1"], index=None, candidates=[]
        )
        self.assertIn("not found", md)


if __name__ == "__main__":
    unittest.main()
