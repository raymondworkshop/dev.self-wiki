import unittest

from fix_provenance_links import fix_content, fix_line
from query_promote import format_promote_suggestion, should_suggest_promote


class TestFixProvenanceLinks(unittest.TestCase):
    def test_compression_arrow_raw(self):
        line = "- [[(Source: [[compression/_posts/foo.md]]) → [[raw/_posts/foo.md]]"
        fixed = fix_line(line)
        self.assertEqual(fixed, "- [[compression/_posts/foo.md]] → [[raw/_posts/foo.md]]")

    def test_discovery_note(self):
        line = "- [[(Source: [[discovery/2026-06-15.md]]) — F3]]"
        fixed = fix_line(line)
        self.assertEqual(fixed, "- [[discovery/2026-06-15.md]] — F3")

    def test_idempotent(self):
        original = "- [[compression/a.md]] → [[raw/b.md]]\n"
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
