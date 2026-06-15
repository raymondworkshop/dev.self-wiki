import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from compress_chunking import iter_units, needs_chunking


class CompressChunkingTests(unittest.TestCase):
    def test_small_file_single_unit(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "origin-apple-notes" / "short.md"
            p.parent.mkdir(parents=True)
            p.write_text("line\n" * 10, encoding="utf-8")
            rel = "origin-apple-notes/short.md"
            units = iter_units(rel, p)
            self.assertEqual(len(units), 1)
            self.assertEqual(units[0][0], rel)

    def test_posts_file_chunks(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "_posts" / "mega.md"
            p.parent.mkdir(parents=True)
            lines = [f"line {i}" for i in range(500)]
            p.write_text("\n".join(lines), encoding="utf-8")
            rel = "_posts/mega.md"
            self.assertTrue(needs_chunking(rel, len(lines)))
            units = iter_units(rel, p)
            self.assertEqual(len(units), 2)
            self.assertEqual(units[0][0], "_posts/mega/part-001.md")
            self.assertEqual(units[1][0], "_posts/mega/part-002.md")


if __name__ == "__main__":
    unittest.main()
