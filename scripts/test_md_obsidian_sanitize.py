"""Tests for Obsidian markdown LaTeX → Unicode sanitization."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from md_obsidian_sanitize import sanitize_markdown_file, sanitize_obsidian_markdown


class ObsidianSanitizeTests(unittest.TestCase):
    def test_arrow_and_neq(self) -> None:
        raw = r"表演性自信 $\rightarrow$ 身份 | 博弈 $\neq$ 乞讨 | F2 $\leftrightarrow$ F6"
        out = sanitize_obsidian_markdown(raw)
        self.assertEqual(out, "表演性自信 → 身份 | 博弈 ≠ 乞讨 | F2 ↔ F6")
        self.assertNotIn("$", out)

    def test_delta(self) -> None:
        self.assertEqual(
            sanitize_obsidian_markdown(r"No prior $\Delta$ exists."),
            "No prior Δ exists.",
        )

    def test_idempotent(self) -> None:
        text = "a → b ≠ c"
        self.assertEqual(sanitize_obsidian_markdown(text), text)

    def test_file_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.md"
            path.write_text("A $\\rightarrow$ B\n", encoding="utf-8")
            self.assertTrue(sanitize_markdown_file(path))
            self.assertEqual(path.read_text(encoding="utf-8"), "A → B\n")
            self.assertFalse(sanitize_markdown_file(path))


if __name__ == "__main__":
    unittest.main()
