import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import query_server


class QueryServerTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(query_server.app)

    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Self-Wiki", response.text)
        self.assertIn("Socratic Mirror", response.text)
        self.assertIn("make query", response.text)

    def test_wiki_index_renders(self):
        response = self.client.get("/wiki")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Wiki", response.text)

    def test_profile_empty_state(self):
        missing = query_server.WORKSPACE_PATH / "twin" / "__missing_profile_test__.md"
        with patch.object(query_server, "TWIN_PROFILE", missing):
            response = self.client.get("/profile")
        self.assertEqual(response.status_code, 200)
        self.assertIn("not generated yet", response.text)

    def test_wikilink_renders_as_href(self):
        html = query_server.markdown_to_html(
            "See (Source: [[self-wiki/wiki/example.md]]) for details.",
            base="outputs",
        )
        self.assertIn('href="/wiki/example.md"', html)

    def test_query_page_uses_query_core(self):
        fake_result = {
            "query": "what are my values?",
            "answer": "# Answer\n\n> grounded summary\n\n## Provenance\n- [[note.md]]",
            "provider": "mlx",
            "model": "test-model",
            "profile": "values",
            "strong_profile": True,
            "profile_scores": {"values": 10},
            "language": "English",
            "query_terms": ["values"],
            "candidates": [
                {
                    "score": 42,
                    "path": "self-wiki/wiki/note.md",
                    "name": "note",
                    "matched_terms": ["values"],
                }
            ],
            "messages": [{"role": "assistant", "content": "answer"}],
            "pending_path": "self-wiki/log/pending/query-test.json",
        }

        with (
            patch.object(query_server, "load_index", return_value={"topics": {}}),
            patch.object(query_server, "generate_query_answer", return_value=fake_result),
            patch.object(
                query_server,
                "save_output",
                return_value=Path("/tmp/what-are-my-values.md"),
            ),
        ):
            response = self.client.post(
                "/query", data={"question": "what are my values?"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("grounded summary", response.text)
        self.assertIn("Retrieved Evidence", response.text)
        self.assertIn("self-wiki/wiki/note.md", response.text)
        self.assertIn('href="/wiki/note.md"', response.text)

    def test_output_page_resolves_symlinked_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_root = Path(tmp) / "real"
            link_root = Path(tmp) / "link"
            real_root.mkdir()
            link_root.symlink_to(real_root)
            note = real_root / "test-note.md"
            note.write_text("# Symlink test\n", encoding="utf-8")

            resolved = query_server.resolve_markdown_path(link_root, "test-note.md")
            self.assertEqual(resolved, note.resolve())

            with patch.object(query_server, "OUTPUT_ROOT", link_root):
                response = self.client.get("/outputs/test-note.md")
            self.assertEqual(response.status_code, 200)
            self.assertIn("Symlink test", response.text)


if __name__ == "__main__":
    unittest.main()
