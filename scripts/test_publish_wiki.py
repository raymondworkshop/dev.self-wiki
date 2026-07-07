import unittest

from publish_wiki import VaultIndex, markdown_body_to_html, normalize_link_target

# Canonical raw path for legacy compression fixtures (see test_fix_provenance.py).
LEGACY_RAW = "raw/origin-apple-notes/亲密关系.md"


class TestPublishWiki(unittest.TestCase):
    def test_normalize_link_target(self):
        self.assertEqual(
            normalize_link_target("../raw/_posts/foo.md"),
            "raw/_posts/foo.md",
        )
        self.assertEqual(
            normalize_link_target("self-wiki/wiki/Communication.md"),
            "wiki/Communication.md",
        )
        self.assertEqual(normalize_link_target("Communication"), "wiki/Communication.md")

    def test_wikilink_display_stem(self):
        files = {
            "wiki/Communication.md": None,
            "raw/origin-apple-notes/亲密关系.md": None,
        }
        index = VaultIndex(files)  # type: ignore[arg-type]
        html_out = markdown_body_to_html(
            "### Distillation (2026-06-16) - source: [[../raw/origin-apple-notes/亲密关系.md]]\n"
            f"Body. (Source: [[{LEGACY_RAW}]])",
            index,
        )
        self.assertIn('class="distillation-heading"', html_out)
        self.assertIn("亲密关系</a>", html_out)
        self.assertNotIn("../raw/", html_out)

    def test_resolve_wikilink(self):
        files = {
            "wiki/Communication.md": None,
            "raw/_posts/new-apple-notes/2026-07-01.md": None,
        }
        index = VaultIndex(files)  # type: ignore[arg-type]
        self.assertEqual(
            index.resolve("raw/_posts/new-apple-notes/2026-07-01.md"),
            "raw/_posts/new-apple-notes/2026-07-01.html",
        )
        self.assertEqual(index.resolve("Communication"), "wiki/Communication.html")

    def test_inline_bullets_become_list(self):
        files = {"wiki/Communication.md": None}
        index = VaultIndex(files)  # type: ignore[arg-type]
        body = (
            "Intro sentence. **[AI Synthesis]** More context. "
            "- first point. - second point. "
            "(Source: [[raw/_posts/foo.md]])"
        )
        html_out = markdown_body_to_html(body, index)
        self.assertIn("<p>Intro sentence.", html_out)
        self.assertIn("<p><strong>[AI Synthesis]</strong> More context.</p>", html_out)
        self.assertIn("<ul>", html_out)
        self.assertIn("<li>first point.</li>", html_out)
        self.assertIn("<li>second point.</li>", html_out)
        self.assertIn('class="source-line"', html_out)

    def test_distillation_heading_class(self):
        files = {"wiki/Communication.md": None}
        index = VaultIndex(files)  # type: ignore[arg-type]
        html_out = markdown_body_to_html(
            "### Distillation (2026-06-16) - source: [[raw/foo.md]]\nOne line.",
            index,
        )
        self.assertIn('class="distillation-heading"', html_out)

    def test_markdown_table(self):
        files = {
            "wiki/Communication.md": None,
            "raw/_posts/new-apple-notes/2026-06-30.md": None,
        }
        index = VaultIndex(files)  # type: ignore[arg-type]
        body = (
            "| ID | Theme | Method |\n"
            "|----|-------|--------|\n"
            "| **F1** | AI boundary | [Literal] · cross-corpus |\n"
            "\n"
            "| Sample | Raw source |\n"
            "|------|------------|\n"
            "| [[raw/_posts/new-apple-notes/2026-06-30.md|AI in work & relationship]] | "
            "[[raw/_posts/new-apple-notes/2026-06-30.md]] |\n"
        )
        html_out = markdown_body_to_html(body, index)
        self.assertIn("<table>", html_out)
        self.assertIn("<th>ID</th>", html_out)
        self.assertIn("<td><strong>F1</strong></td>", html_out)
        self.assertIn("AI in work &amp; relationship</a>", html_out)
        self.assertNotIn("<p>|", html_out)

    def test_mermaid_not_html_escaped(self):
        files = {"wiki/Communication.md": None}
        index = VaultIndex(files)  # type: ignore[arg-type]
        body = '## Theme map\n\n```mermaid\nsubgraph ar ["AI & Relationship"]\n  F1 --> N1\nend\n```\n'
        html_out = markdown_body_to_html(body, index)
        self.assertIn('subgraph ar ["AI & Relationship"]', html_out)
        self.assertNotIn("&amp;", html_out)

    def test_strip_agent_markdown_fence(self):
        from publish_wiki import _parse_frontmatter

        wrapped = "```markdown\n---\ntitle: Test\n---\n\nBody.\n```\n"
        meta, body = _parse_frontmatter(wrapped)
        self.assertEqual(meta.get("title"), "Test")
        self.assertEqual(body.strip(), "Body.")

    def test_html_comments_stripped(self):
        files = {"wiki/Communication.md": None}
        index = VaultIndex(files)  # type: ignore[arg-type]
        html_out = markdown_body_to_html(
            "Line one.\n<!-- END BACKLINKS -->\nLine two.",
            index,
        )
        self.assertNotIn("BACKLINKS", html_out)
        self.assertIn("Line one.", html_out)
        self.assertIn("Line two.", html_out)


if __name__ == "__main__":
    unittest.main()
