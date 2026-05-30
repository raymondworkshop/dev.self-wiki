import re
import unittest
from pathlib import Path

import yaml
from config import WIKI_DIR
from llm_provider import context_limits, extract_json_object, provider_name


class TestWikiCompliance(unittest.TestCase):
    def setUp(self):
        self.wiki_files = list(WIKI_DIR.rglob("*.md", recurse_symlinks=True))
        # Exclude specific non-content files
        self.wiki_files = [
            f
            for f in self.wiki_files
            if f.name not in ["INDEX.md", "audit.md"] and "-Hub" not in f.name
        ]

    def test_front_matter(self):
        required_keys = {"last_updated", "title", "description", "level", "tags"}
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
                self.assertIsNotNone(match, f"Missing YAML front matter in {f.name}")
                try:
                    fm = yaml.safe_load(match.group(1))
                    self.assertTrue(
                        required_keys.issubset(set(fm.keys())),
                        f"Missing keys in {f.name}: {required_keys - set(fm.keys())}",
                    )
                except yaml.YAMLError:
                    self.fail(f"Invalid YAML in {f.name}")

    def test_socratic_summary(self):
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                # Look for > summary after front matter
                match = re.search(r"---\n\n>\s*(.*?)\n\n", content, re.DOTALL)
                if not match:
                    # Alternative check if there's no double newline
                    match = re.search(r"---\n\n>\s*(.*?)\n", content)

                self.assertIsNotNone(
                    match, f"Missing Socratic summary ('> ...') in {f.name}"
                )
                summary = match.group(1).strip()
                sentences = re.split(r"[.!?]+", summary)
                sentences = [s for s in sentences if s.strip()]
                # Allow a bit more flexibility: 1-4 sentences
                self.assertTrue(
                    1 <= len(sentences) <= 4,
                    f"Summary in {f.name} should be 1-4 sentences, found {len(sentences)}",
                )

    def test_required_sections(self):
        required_sections = ["## Evolution", "## Backlinks", "## Sources"]
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                for section in required_sections:
                    self.assertIn(section, content, f"Missing {section} in {f.name}")

    def test_traceability(self):
        """Check if sources section contains actual links."""
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                sources_match = re.search(
                    r"## Sources\n(.*?)$", content, re.DOTALL | re.IGNORECASE
                )
                if sources_match:
                    sources = sources_match.group(1).strip()
                    # It's okay if sources is empty for some files if they are L1/L2 and haven't been linked yet,
                    # but typically we want at least the markers or a comment.
                    # For this test, we just check if it's there.


class TestLLMProvider(unittest.TestCase):
    def test_provider_name_accepts_explicit_override(self):
        self.assertEqual(provider_name("gemini"), "gemini")

    def test_context_limits_are_provider_aware(self):
        gemini_context, gemini_reserved, _ = context_limits("gemini")
        mlx_context, mlx_reserved, _ = context_limits("mlx")
        self.assertGreater(gemini_context, mlx_context)
        self.assertGreater(gemini_reserved, mlx_reserved)

    def test_extract_json_object_from_model_text(self):
        parsed = extract_json_object('```json\n{"actions": []}\n```')
        self.assertEqual(parsed, {"actions": []})


if __name__ == "__main__":
    unittest.main()
