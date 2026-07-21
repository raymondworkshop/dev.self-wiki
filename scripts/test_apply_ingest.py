import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from apply_ingest import apply_actions
from wiki_synth_manifest import list_resume_targets


class TestApplyIngest(unittest.TestCase):
    def test_creates_page_with_agents_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki_dir = root / "self-wiki" / "wiki"
            wiki_dir.mkdir(parents=True)
            with mock.patch("config.WORKSPACE_PATH", root), mock.patch(
                "config.WIKI_DIR", wiki_dir
            ), mock.patch("models.WIKI_DIR", wiki_dir), mock.patch(
                "wiki_themes.WIKI_DIR", wiki_dir
            ), mock.patch("wiki_themes.WORKSPACE_PATH", root):
                data = {
                    "raw_path": "raw/_posts/example.md",
                    "actions": [
                        {
                            "target_title": "Test Theme",
                            "confidence_score": 0.85,
                            "summary": "A distilled theme.",
                            "new_body_content": "Key insight from raw.",
                            "tags": ["type/synthesis"],
                            "level": 1,
                        }
                    ],
                }
                updated = apply_actions(data, rel_path="_posts/example.md")
                self.assertEqual(updated, 1)
                page_path = wiki_dir / "Test Theme.md"
                self.assertTrue(page_path.is_file())
                text = page_path.read_text(encoding="utf-8")
                self.assertIn("- source: [[../raw/_posts/example.md]]", text)
                self.assertIn("Key insight from raw.", text)

    def test_merge_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki_dir = root / "self-wiki" / "wiki"
            wiki_dir.mkdir(parents=True)
            with mock.patch("config.WORKSPACE_PATH", root), mock.patch(
                "config.WIKI_DIR", wiki_dir
            ), mock.patch("models.WIKI_DIR", wiki_dir), mock.patch(
                "wiki_themes.WIKI_DIR", wiki_dir
            ), mock.patch("wiki_themes.WORKSPACE_PATH", root):
                data = {
                    "actions": [
                        {
                            "target_title": "Dup Theme",
                            "new_body_content": "Same body.",
                            "tags": ["type/synthesis"],
                        }
                    ],
                }
                first = apply_actions(data, rel_path="_posts/a.md")
                second = apply_actions(data, rel_path="_posts/a.md")
                self.assertEqual(first, 1)
                self.assertEqual(second, 1)
                text = (wiki_dir / "Dup Theme.md").read_text(encoding="utf-8")
                self.assertEqual(text.count("### Distillation"), 1)


class TestManifestChangedFiles(unittest.TestCase):
    def test_failed_file_stays_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = root / "self-wiki" / "raw" / "_posts"
            log_dir = root / "self-wiki" / "log"
            raw_dir.mkdir(parents=True)
            log_dir.mkdir(parents=True)
            raw_file = raw_dir / "note.md"
            raw_file.write_text("# note\nbody", encoding="utf-8")
            manifest = {
                "version": 2,
                "files": {
                    "self-wiki/raw/_posts/note.md": {
                        "status": "failed",
                        "content_hash": "deadbeef",
                        "raw_path": "self-wiki/raw/_posts/note.md",
                    }
                },
                "summary": {},
            }
            manifest_path = log_dir / "wiki_synth_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with mock.patch("config.WORKSPACE_PATH", root), mock.patch(
                "wiki_synth_manifest.WORKSPACE_PATH", root
            ), mock.patch("wiki_synth_manifest.RAW_DIR", raw_dir), mock.patch(
                "wiki_synth_manifest.LOG_DIR", log_dir
            ), mock.patch("wiki_synth_manifest.MANIFEST_JSON", manifest_path), mock.patch(
                "wiki_synth_manifest.seed_manifest_from_wiki_provenance", return_value=0
            ), mock.patch(
                "wiki_synth_manifest.resolve_profile",
                return_value={
                    "wiki_skill": "skills/wiki-synthesize.md",
                    "max_theme_updates": 2,
                },
            ):
                targets = list_resume_targets()
                self.assertEqual(len(targets), 1)
                self.assertIn("note.md", targets[0][0])


    def test_origin_apple_notes_folder_alias(self):
        # Folder filtering uses prefix matching on the manifest "inner" raw path:
        # list_resume_targets(folder=...) includes only entries whose inner path starts with `folder/`.
        from wiki_synth_manifest import list_resume_targets

        scan_data = {
            "files": {
                "self-wiki/raw/origin-apple-notes/a.md": {"status": "pending"},
                "self-wiki/raw/_posts/origin-apple-notes/b.md": {"status": "pending"},
                "self-wiki/raw/new-apple-notes/c.md": {"status": "pending"},
            }
        }

        with mock.patch("wiki_synth_manifest.scan_all") as scan:
            scan.return_value = scan_data
            with mock.patch("wiki_synth_manifest.WORKSPACE_PATH", Path("/tmp/ws")), mock.patch(
                "pathlib.Path.is_file", return_value=True
            ):
                targets = list_resume_targets(folder="origin-apple-notes")
                self.assertEqual(len(targets), 1)
                self.assertIn("origin-apple-notes/a.md", targets[0][0])

                targets2 = list_resume_targets(folder="new-apple-notes")
                self.assertEqual(len(targets2), 1)
                self.assertIn("new-apple-notes/c.md", targets2[0][0])


if __name__ == "__main__":
    unittest.main()
