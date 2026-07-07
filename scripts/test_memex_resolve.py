"""Tests for memex wikilink resolution."""

from __future__ import annotations

import unittest

from memex.resolve import normalize_key, resolve_target
from memex.sources import VaultPage


def _registry(*pages: VaultPage) -> dict:
    from memex.resolve import register_target

    reg: dict = {}
    for p in pages:
        register_target(
            reg,
            p.title,
            p.url,
            stem=p.stem,
            aliases=[p.stem],
            rel=p.rel,
        )
    return reg


class TestMemexResolve(unittest.TestCase):
    def test_exact_title_match(self) -> None:
        page = VaultPage(
            rel="wiki/Learning.md",
            path=__import__("pathlib").Path("wiki/Learning.md"),
            title="Learning",
            body="",
            layer="wiki",
        )
        reg = _registry(page)
        entry = resolve_target("Learning", reg)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry["url"], "/wiki/Learning.html")

    def test_path_match(self) -> None:
        page = VaultPage(
            rel="raw/_posts/foo.md",
            path=__import__("pathlib").Path("raw/_posts/foo.md"),
            title="Foo",
            body="",
            layer="raw",
        )
        reg = _registry(page)
        entry = resolve_target("raw/_posts/foo.md", reg)
        self.assertIsNotNone(entry)

    def test_normalize_key_strips_quotes(self) -> None:
        self.assertEqual(normalize_key('"Hello"'), "hello")


if __name__ == "__main__":
    unittest.main()
