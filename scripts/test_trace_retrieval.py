"""Chinese / English query term extraction for trace retrieval."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from trace_retrieval import (
    effective_kind,
    parse_query_and_scope,
    query_literal_terms,
    recency_boost,
    resolve_scope_paths,
    score_paragraph,
)


class QueryLiteralTermsTests(unittest.TestCase):
    def test_english_stopwords(self) -> None:
        terms = query_literal_terms("what are my core values")
        self.assertIn("core", terms)
        self.assertIn("values", terms)
        self.assertNotIn("what", terms)
        self.assertNotIn("are", terms)
        self.assertNotIn("my", terms)

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

    def test_zh_question_particles_and_frames(self) -> None:
        terms = query_literal_terms("什麼是自由？ 愛呢？")
        self.assertIn("自由", terms)
        self.assertIn("愛", terms)
        self.assertNotIn("愛呢", terms)
        self.assertNotIn("什麼是自由", terms)
        love = {
            "text": "愛一個人，你就會看到他們表相之後的本質。",
            "path": "raw/_posts/2020-05-19-courage-and-love.md",
            "file": "2020-05-19-courage-and-love.md",
            "kind": "post",
        }
        free_title = {
            "text": "自由上网的喜悦",
            "path": "raw/_posts/origin-apple-notes/自由上网的喜悦.md",
            "file": "自由上网的喜悦.md",
            "kind": "apple-notes",
        }
        self.assertGreater(score_paragraph(love, terms), 0)
        # Both topics should score; love must not be zeroed by particle glue.
        self.assertGreater(score_paragraph(love, terms), 10)

    def test_long_post_outranks_title_stub(self) -> None:
        terms = query_literal_terms("什麼是自由？")
        essay = {
            "text": (
                "真正的财务自由，应先让心灵自由，然后从现实出发，反推实现自由的条件，"
                "再以非任性的克制去贯彻这种自由。人们往往把任性叫做自由。"
                "自由是有信心做自己，不做别人期望的自己。"
            ),
            "path": "raw/_posts/diary/2022-08-08-the-log-of-your-life.md",
            "file": "2022-08-08-the-log-of-your-life.md",
            "kind": "post",
        }
        stub = {
            "text": "自由上网的喜悦",
            "path": "raw/_posts/origin-apple-notes/自由上网的喜悦.md",
            "file": "自由上网的喜悦.md",
            "kind": "apple-notes",
        }
        self.assertGreater(score_paragraph(essay, terms), score_paragraph(stub, terms))

    def test_synonyms_and_frontmatter(self) -> None:
        terms = query_literal_terms("什麼是自由？")
        self.assertIn("free", terms)
        self.assertIn("freedom", terms)
        body = {
            "text": "#### 人生的自由\n\n* **做你能做的**\n- 給自己拍拍肩",
            "path": "raw/_posts/2026-03-01-a-free-man.md",
            "file": "2026-03-01-a-free-man.md",
            "kind": "post",
        }
        fm = {
            "text": '---\ntitle: "Notes on \'成為自由人\'"\nrelated: [About Coaching]\n---',
            "path": "raw/_posts/2026-03-01-a-free-man.md",
            "file": "2026-03-01-a-free-man.md",
            "kind": "post",
        }
        primary = ["自由"]
        self.assertGreater(
            score_paragraph(body, terms, primary_terms=primary),
            score_paragraph(fm, terms, primary_terms=primary),
        )
        # Filename "free" must not score a paragraph that never mentions 自由/free.
        unrelated = {
            "text": "與人相處的摩擦不過是萬物流轉的必然現象，保持平常心即可。",
            "path": "raw/_posts/2026-03-01-a-free-man.md",
            "file": "2026-03-01-a-free-man.md",
            "kind": "post",
        }
        self.assertEqual(
            score_paragraph(unrelated, terms, primary_terms=primary),
            0,
        )

    def test_kind_and_recency_tiers(self) -> None:
        terms = ["自由"]
        now = datetime(2026, 9, 30)
        base = {
            "text": "真正的自由是有信心做自己，心灵自由先于财务自由。",
            "file": "x.md",
        }
        post = {
            **base,
            "path": "raw/_posts/2026-03-01-a-free-man.md",
            "file": "2026-03-01-a-free-man.md",
            "kind": "post",
        }
        note = {
            **base,
            "path": "raw/_posts/origin-apple-notes/自由上网的喜悦.md",
            "file": "自由上网的喜悦.md",
            "kind": "apple-notes",
        }
        tweet = {
            **base,
            "path": "raw/_posts/twitter/twitter-likes-001.md",
            "file": "twitter-likes-001.md",
            "kind": "twitter",
        }
        self.assertEqual(effective_kind(post), "post")
        self.assertEqual(effective_kind(note), "apple-notes")
        self.assertEqual(effective_kind(tweet), "twitter")
        self.assertGreater(
            score_paragraph(post, terms, primary_terms=terms, now=now),
            score_paragraph(note, terms, primary_terms=terms, now=now),
        )
        self.assertGreater(
            score_paragraph(note, terms, primary_terms=terms, now=now),
            score_paragraph(tweet, terms, primary_terms=terms, now=now),
        )
        recent = {
            **base,
            "path": "raw/_posts/2026-08-01-newer.md",
            "file": "2026-08-01-newer.md",
            "kind": "post",
        }
        old = {
            **base,
            "path": "raw/_posts/2014-08-01-older.md",
            "file": "2014-08-01-older.md",
            "kind": "post",
        }
        self.assertGreater(recency_boost(recent, now=now), recency_boost(old, now=now))
        self.assertGreater(
            score_paragraph(recent, terms, primary_terms=terms, now=now),
            score_paragraph(old, terms, primary_terms=terms, now=now),
        )

    def test_parse_inline_scope(self) -> None:
        q, scope = parse_query_and_scope("什麼是自由？ @a-free-man")
        self.assertEqual(q, "什麼是自由？")
        self.assertEqual(scope, "a-free-man")
        q2, scope2 = parse_query_and_scope("什麼是自由？", scope="raw/_posts/x.md")
        self.assertEqual(scope2, "raw/_posts/x.md")
        self.assertIsNone(parse_query_and_scope("無範圍")[1])


if __name__ == "__main__":
    unittest.main()
