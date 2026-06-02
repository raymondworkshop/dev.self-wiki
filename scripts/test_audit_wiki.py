import unittest

from audit_wiki import (
    collect_level2_soft_warnings,
    find_duplicate_themes,
)


class AuditWikiTests(unittest.TestCase):
    def test_find_duplicate_themes_by_title(self):
        pages = [
            {"title": "Soft Skills Growth", "tags": ["type/synthesis"]},
            {"title": "Soft Skills Growth Guide", "tags": ["type/synthesis"]},
            {"title": "Unrelated Topic", "tags": ["type/synthesis"]},
        ]
        warnings = find_duplicate_themes(pages, threshold=0.75, tag_threshold=0.99)
        joined = "\n".join(warnings)
        self.assertIn("Soft Skills Growth", joined)
        self.assertNotIn("Unrelated Topic", joined)

    def test_find_duplicate_themes_by_tag_cluster(self):
        pages = [
            {"title": "Leadership Style A", "tags": ["type/principle", "domain/leadership"]},
            {"title": "Leadership Style B", "tags": ["type/principle", "domain/leadership"]},
            {"title": "Values Core", "tags": ["type/principle", "domain/values"]},
        ]
        warnings = find_duplicate_themes(pages, threshold=0.99, tag_threshold=0.70)
        joined = "\n".join(warnings)
        self.assertIn("Leadership Style A", joined)
        self.assertIn("type/principle", joined)
        self.assertNotIn("Values Core", joined)

    def test_level2_soft_warnings_advisory(self):
        pages = [
            {
                "title": "Weak Principle",
                "content": """---
title: Weak Principle
level: 2
confidence: 0.4
tags: [type/synthesis]
---
> summary
""",
            }
        ]
        warnings = collect_level2_soft_warnings(pages)
        joined = "\n".join(warnings)
        self.assertIn("type/principle", joined)
        self.assertIn("confidence 0.4", joined)


if __name__ == "__main__":
    unittest.main()
