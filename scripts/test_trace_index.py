"""trace index: skip qa/, follow symlink dirs, drop identical copies."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.resolve()))

import trace_index


class GeneratedRawSkipTests(unittest.TestCase):
    def test_is_generated_raw(self) -> None:
        self.assertTrue(trace_index._is_generated_raw("qa/请分析我的价值观.md"))
        self.assertTrue(trace_index._is_generated_raw("qa/nested/x.md"))
        self.assertFalse(trace_index._is_generated_raw("_posts/diary.md"))
        self.assertFalse(trace_index._is_generated_raw("origin-apple-notes/a.md"))

    def test_iter_skips_qa_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "qa").mkdir()
            (raw / "qa" / "generated.md").write_text("generated values\n", encoding="utf-8")
            (raw / "_posts").mkdir()
            keep = raw / "_posts" / "note.md"
            keep.write_text("original note\n", encoding="utf-8")
            with patch.object(trace_index, "RAW_DIR", raw):
                files = trace_index.iter_raw_md_files()
            self.assertEqual(files, [keep])

    def test_iter_follows_symlink_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            target = root / "blog_posts"
            raw.mkdir()
            target.mkdir()
            linked = target / "post.md"
            linked.write_text("from symlink\n", encoding="utf-8")
            os.symlink(target, raw / "_posts", target_is_directory=True)
            (raw / "local.md").write_text("local\n", encoding="utf-8")
            with patch.object(trace_index, "RAW_DIR", raw):
                files = trace_index.iter_raw_md_files()
            names = sorted(p.name for p in files)
            self.assertEqual(names, ["local.md", "post.md"])

    def test_dedupes_identical_twitter_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "twitter").mkdir()
            (raw / "_posts" / "twitter").mkdir(parents=True)
            body = "same like bookmark\n" * 20
            keep = raw / "twitter" / "twitter-likes-001.md"
            mirror = raw / "_posts" / "twitter" / "twitter-likes-001.md"
            keep.write_text(body, encoding="utf-8")
            mirror.write_text(body, encoding="utf-8")
            unique = raw / "_posts" / "only-in-blog.md"
            unique.write_text("blog only\n", encoding="utf-8")
            with patch.object(trace_index, "RAW_DIR", raw):
                files = trace_index.iter_raw_md_files()
                rels = sorted(trace_index._vault_raw_rel(p) for p in files)
            self.assertEqual(
                rels,
                ["_posts/only-in-blog.md", "twitter/twitter-likes-001.md"],
            )


class IncrementalIndexTests(unittest.TestCase):
    def test_incremental_reuses_unchanged_and_updates_one_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            index_json = root / "trace-index.json"
            raw.mkdir()
            a = raw / "a.md"
            b = raw / "b.md"
            a.write_text("alpha paragraph\n\nmore alpha\n", encoding="utf-8")
            b.write_text("beta paragraph\n", encoding="utf-8")

            with (
                patch.object(trace_index, "RAW_DIR", raw),
                patch.object(trace_index, "TRACE_INDEX_JSON", index_json),
            ):
                first = trace_index.build_index(force=True)
                self.assertEqual(first["file_count"], 2)
                first_digest = first["digest"]
                a_paras_before = [
                    p for p in first["paragraphs"] if p["path"] == "raw/a.md"
                ]
                self.assertGreaterEqual(len(a_paras_before), 1)

                # Unchanged rebuild should no-op
                noop = trace_index.build_index(force=False)
                self.assertEqual(noop["digest"], first_digest)

                # Change only b.md → incremental should rebuild b, reuse a
                import time

                time.sleep(0.01)
                b.write_text("beta paragraph updated\n\nsecond\n", encoding="utf-8")
                second = trace_index.build_index(force=False)
                self.assertNotEqual(second["digest"], first_digest)
                a_paras_after = [
                    p for p in second["paragraphs"] if p["path"] == "raw/a.md"
                ]
                b_paras_after = [
                    p for p in second["paragraphs"] if p["path"] == "raw/b.md"
                ]
                self.assertEqual(a_paras_before, a_paras_after)
                self.assertTrue(any("updated" in (p.get("text") or "") for p in b_paras_after))
                self.assertEqual(second["file_count"], 2)

                # Delete a.md → dropped from index
                a.unlink()
                third = trace_index.build_index(force=False)
                self.assertEqual(third["file_count"], 1)
                self.assertTrue(all(p["path"] == "raw/b.md" for p in third["paragraphs"]))


if __name__ == "__main__":
    unittest.main()
