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
        self.assertIn("Ask your self-wiki", response.text)
        self.assertIn("Socratic Mirror", response.text)

    def test_query_page_uses_query_core(self):
        fake_result = {
            "query": "what are my values?",
            "answer": "# Answer\n\n> grounded summary\n\n## Provenance\n- [[note.md]]",
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


if __name__ == "__main__":
    unittest.main()
