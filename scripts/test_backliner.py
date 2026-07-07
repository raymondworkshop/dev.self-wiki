import unittest

from memex.backliner import build_typed_edges
from memex.sources import VaultPage


class TestBacklinerContradicts(unittest.TestCase):
    def _page(self, title: str, body: str) -> VaultPage:
        return VaultPage(
            rel="wiki/Test.md",
            path=None,  # type: ignore[arg-type]
            title=title,
            body=body,
            meta={},
            layer="wiki",
            section="wiki",
        )

    def test_source_trail_only_not_contradict(self):
        body = (
            "### Distillation - source: [[raw/foo.md]]\n"
            "Prose mentions 冲突 in the narrative.\n"
            "(Source: [[raw/foo.md]])\n"
        )
        registry = {
            "raw/foo.md": {
                "title": "foo",
                "url": "/raw/foo.html",
                "rel": "raw/foo.md",
            },
            "wiki/Test.md": {
                "title": "Test",
                "url": "/wiki/Test.html",
                "rel": "wiki/Test.md",
            },
        }
        typed = build_typed_edges([self._page("Test", body)], registry)
        contradicts = typed.get("/wiki/Test.html", {}).get("Contradicts", [])
        self.assertEqual(contradicts, [])

    def test_filename_keyword_not_contradict(self):
        body = (
            "- 2026-06-16: Distilled from raw source "
            "[[raw/origin-apple-notes/决不要反驳别人.md]].\n"
        )
        registry = {
            "raw/origin-apple-notes/决不要反驳别人.md": {
                "title": "决不要反驳别人",
                "url": "/raw/x.html",
                "rel": "raw/origin-apple-notes/决不要反驳别人.md",
            },
            "wiki/Test.md": {
                "title": "Test",
                "url": "/wiki/Test.html",
                "rel": "wiki/Test.md",
            },
        }
        typed = build_typed_edges([self._page("Test", body)], registry)
        contradicts = typed.get("/wiki/Test.html", {}).get("Contradicts", [])
        self.assertEqual(contradicts, [])

    def test_body_wikilink_with_keyword_is_contradict(self):
        body = (
            "Tension with [[wiki/Other.md]] because this 矛盾 is explicit.\n"
        )
        registry = {
            "wiki/Other.md": {
                "title": "Other",
                "url": "/wiki/Other.html",
                "rel": "wiki/Other.md",
            },
            "wiki/Test.md": {
                "title": "Test",
                "url": "/wiki/Test.html",
                "rel": "wiki/Test.md",
            },
        }
        typed = build_typed_edges([self._page("Test", body)], registry)
        contradicts = typed.get("/wiki/Test.html", {}).get("Contradicts", [])
        self.assertEqual(len(contradicts), 1)
        self.assertEqual(contradicts[0]["title"], "Other")


if __name__ == "__main__":
    unittest.main()
