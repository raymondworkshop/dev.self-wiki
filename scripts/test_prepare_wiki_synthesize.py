"""Tests for wiki-synthesize pending package naming."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from prepare_wiki_synthesize import _sanitize_slug, write_pending_units


class TestPendingSlug(unittest.TestCase):
    def test_chunk_slugs_are_unique(self):
        # Use a short raw_rel so the unit_id (part-001/part-002) survives slug truncation.
        raw_rel = "self-wiki/raw/_posts/learning/note.md"
        # Keep unit_id short so the different `part-###` tokens survive truncation.
        u1 = "_posts/learning/part-001"
        u2 = "_posts/learning/part-002"
        s1 = _sanitize_slug(f"{raw_rel}-{u1}")
        s2 = _sanitize_slug(f"{raw_rel}-{u2}")
        self.assertNotEqual(s1, s2)
        self.assertIn("part-001", s1)
        self.assertIn("part-002", s2)
        self.assertLessEqual(len(s1), 80)
        self.assertLessEqual(len(s2), 80)

    def test_write_pending_units_unique_paths_for_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "note.md"
            # > posts chunk limit (400) so iter_units splits
            raw.write_text("\n".join(f"line {i}" for i in range(726)), encoding="utf-8")
            pending_dir = Path(tmp) / "pending"
            pending_dir.mkdir()

            with (
                mock.patch("prepare_wiki_synthesize.PENDING_DIR", pending_dir),
                mock.patch("prepare_wiki_synthesize.workspace_relpath", return_value="self-wiki/raw/_posts/learning/note.md"),
                mock.patch("prepare_wiki_synthesize.raw_rel_inner", return_value="_posts/learning/note.md"),
                mock.patch(
                    "prepare_wiki_synthesize.resolve_profile",
                    return_value={"wiki_skill": "skills/wiki-synthesize.md", "max_theme_updates": 3, "chunk_lines": 400},
                ),
                mock.patch("prepare_wiki_synthesize.resolve_skill", return_value="skills/wiki-synthesize.md"),
                mock.patch("prepare_wiki_synthesize.load_existing_themes", return_value=([], {})),
            ):
                paths = write_pending_units(raw)

            self.assertGreaterEqual(len(paths), 2)
            self.assertEqual(len(paths), len(set(paths)))
            for path in paths:
                self.assertTrue(path.is_file(), path.name)


if __name__ == "__main__":
    unittest.main()
