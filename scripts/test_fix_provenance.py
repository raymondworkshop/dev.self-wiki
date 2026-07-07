import unittest

from fix_provenance_links import (
    canonical_wikilink_target,
    fix_content,
    fix_line,
    wikilink_display_label,
)
from query_promote import format_promote_suggestion, should_suggest_promote


# Legacy compression/ paths (retired layer) still normalize to raw/ for old wiki links.
LEGACY_COMPRESSION = "compression/origin-apple-notes/亲密关系.md"
LEGACY_RAW = "raw/origin-apple-notes/亲密关系.md"


class TestFixProvenanceLinks(unittest.TestCase):
    def test_raw_arrow_raw(self):
        line = f"- [[(Source: [[compression/_posts/foo.md]]) → [[raw/_posts/foo.md]]"
        fixed = fix_line(line)
        self.assertEqual(fixed, "- [[raw/_posts/foo.md]] → [[raw/_posts/foo.md]]")

    def test_discovery_note(self):
        line = "- [[(Source: [[discovery/2026-06-15.md]]) — F3]]"
        fixed = fix_line(line)
        self.assertEqual(fixed, "- [[discovery/2026-06-15.md]] — F3")

    def test_normalize_relative_raw_wikilink(self):
        line = "### Distillation (2026-06-16) - source: [[../raw/origin-apple-notes/亲密关系.md]]"
        fixed = fix_line(line)
        self.assertEqual(
            fixed,
            "### Distillation (2026-06-16) - source: [[raw/origin-apple-notes/亲密关系.md]]",
        )

    def test_legacy_compression_maps_to_raw(self):
        """compression/ → raw/ in inline sources and canonical targets."""
        line = f"Some prose. (Source: [[{LEGACY_COMPRESSION}]])"
        self.assertEqual(fix_line(line), f"Some prose. (Source: [[{LEGACY_RAW}]])")
        self.assertEqual(
            canonical_wikilink_target("compression/origin-apple-notes/x.md"),
            "raw/origin-apple-notes/x.md",
        )

    def test_canonical_wikilink_target(self):
        self.assertEqual(
            canonical_wikilink_target("../raw/_posts/foo.md"),
            "raw/_posts/foo.md",
        )

    def test_wikilink_display_label(self):
        self.assertEqual(
            wikilink_display_label("../raw/origin-apple-notes/亲密关系.md"),
            "亲密关系",
        )

    def test_idempotent(self):
        original = "- [[raw/a.md]] → [[raw/b.md]]\n"
        fixed, n = fix_content(original)
        self.assertEqual(n, 0)
        self.assertEqual(fixed, original)


class TestQueryPromote(unittest.TestCase):
    def test_detects_cognitive_shift(self):
        self.assertTrue(should_suggest_promote("A [Cognitive Shift] here"))

    def test_suggestion_includes_make_promote(self):
        text = format_promote_suggestion(
            answer="[Cognitive Shift] tension",
            output_path="self-wiki/outputs/foo.md",
            candidates=[{"title": "先利益后逻辑", "score": 0.9}],
            query="test",
        )
        self.assertIsNotNone(text)
        assert text is not None
        self.assertIn("make promote", text)
        self.assertIn("先利益后逻辑", text)


if __name__ == "__main__":
    unittest.main()
