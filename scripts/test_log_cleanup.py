"""Tests for log_cleanup and newest-first log.md."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

import log_cleanup
import log_utils


class LogCleanupTests(unittest.TestCase):
    def test_append_log_dedupes_identical_top_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            log_md = log_dir / "log.md"
            log_cleanup.LOG_DIR = log_dir
            log_cleanup.LOG_MD = log_md
            log_utils.LOG_DIR = log_dir
            log_utils.LOG_MD = log_md

            log_utils.append_log("ingest", "post-ingest complete")
            log_utils.append_log("ingest", "post-ingest complete")
            text = log_md.read_text(encoding="utf-8")
            self.assertEqual(text.count("post-ingest complete"), 1)

    def test_append_log_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            log_md = log_dir / "log.md"
            log_utils.LOG_DIR = log_dir
            log_utils.LOG_MD = log_md

            log_utils.append_log("ingest", "older")
            log_utils.append_log("rbrain", "newer")
            text = log_md.read_text(encoding="utf-8")
            newer_pos = text.index("newer")
            older_pos = text.index("older")
            self.assertLess(newer_pos, older_pos)

    def test_trim_log_md_keeps_recent_entries_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            log_md = log_dir / "log.md"
            log_cleanup.LOG_DIR = log_dir
            log_cleanup.LOG_MD = log_md

            # Newest first: entry 9 at top, entry 0 at bottom
            lines = ["# Self-Wiki Log\n", "\n"]
            for i in range(9, -1, -1):
                lines.append(f"## [2026-06-{i + 1:02d}] ingest | entry {i}\n")
            log_md.write_text("".join(lines), encoding="utf-8")

            removed = log_cleanup.trim_log_md(max_entries=4)
            self.assertEqual(removed, 6)
            kept = log_md.read_text(encoding="utf-8")
            self.assertIn("entry 9", kept)
            self.assertIn("entry 6", kept)
            self.assertNotIn("entry 0", kept)
            self.assertLess(kept.index("entry 9"), kept.index("entry 6"))

    def test_rotate_file_truncates_large_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.log"
            path.write_text("x" * 200 + "\nKEEP\n", encoding="utf-8")
            rotated = log_cleanup.rotate_file(path, max_bytes=50, keep_tail_bytes=20)
            self.assertTrue(rotated)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("... [truncated]"))
            self.assertIn("KEEP", text)


if __name__ == "__main__":
    unittest.main()
