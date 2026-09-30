"""Chinese / English query term extraction for trace retrieval."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from trace_retrieval import query_literal_terms, score_paragraph


class QueryLiteralTermsTests(unittest.TestCase):
    def test_english_stopwords(self) -> None:
        self.assertEqual(query_literal_terms("what are my core values"), ["core", "values"])

    def test_chinese_short_phrase_kept(self) -> None:
        terms = query_literal_terms("价值观")
        self.assertIn("价值观", terms)

    def test_chinese_question_expands_ngrams(self) -> None:
        terms = query_literal_terms("我的核心价值观是什么")
        self.assertNotIn("我的核心价值观是什么", terms)
        self.assertIn("价值观", terms)
        self.assertIn("核心", terms)
        self.assertNotIn("我的", terms)
        self.assertNotIn("什么", terms)
        self.assertNotIn("是什么", terms)

    def test_score_hits_partial_chinese(self) -> None:
        para = {
            "text": "我一直在想自己的价值观和原则。",
            "path": "raw/_posts/x.md",
            "file": "x.md",
            "kind": "post",
        }
        terms = query_literal_terms("我的核心价值观是什么")
        self.assertGreater(score_paragraph(para, terms), 0)


if __name__ == "__main__":
    unittest.main()
