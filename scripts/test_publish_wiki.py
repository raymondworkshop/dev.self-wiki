import unittest

from publish_wiki import VaultIndex, normalize_link_target


class TestPublishWiki(unittest.TestCase):
    def test_normalize_link_target(self):
        self.assertEqual(
            normalize_link_target("../raw/_posts/foo.md"),
            "raw/_posts/foo.md",
        )
        self.assertEqual(
            normalize_link_target("self-wiki/wiki/Communication.md"),
            "wiki/Communication.md",
        )
        self.assertEqual(normalize_link_target("Communication"), "wiki/Communication.md")

    def test_resolve_wikilink(self):
        files = {
            "wiki/Communication.md": None,
            "raw/_posts/new-apple-notes/2026-07-01.md": None,
            "compression/_posts/new-apple-notes/2026-07-01.md": None,
        }
        index = VaultIndex(files)  # type: ignore[arg-type]
        self.assertEqual(
            index.resolve("raw/_posts/new-apple-notes/2026-07-01.md"),
            "raw/_posts/new-apple-notes/2026-07-01.html",
        )
        self.assertEqual(index.resolve("Communication"), "wiki/Communication.html")


if __name__ == "__main__":
    unittest.main()
