import tempfile
import unittest
from pathlib import Path

from build_twin_profile import (
    _build_essence,
    _collect_judged_hypotheses,
    _dedupe_principles,
    _evolution_line_qualifies,
    _grounded_in_personal_raw,
    _has_coexistence_signal,
    _hypothesis_included,
    _is_evolution_noise,
    _parse_hypothesis_blocks,
    _principle_affinity,
    _qualifies_principle,
)


SAMPLE_HYPOTHESES = """# Self-Hypotheses

## H-aaa: decision

Status: uncertain
Confidence: medium
Category: decision-logic

Claim:
I delay hard career decisions.

Evidence:
- [[x]]

User Judgment:
revised

Notes:
fear of responsibility

## H-bbb: relationships

Status: supported
Confidence: medium
Category: relationship-patterns

Claim:
Autonomy-first co-creation OS for relationships.

User Judgment:
revised

Notes:
None

## H-ccc: junk

Status: rejected
Confidence: low
Category: other

Claim:
Should be excluded.

User Judgment:
rejected

Notes:
None
"""


class TestTwinProfileFilters(unittest.TestCase):
    def test_grounding_accepts_posts_and_apple_notes(self):
        self.assertTrue(
            _grounded_in_personal_raw("(Source: [[raw/_posts/learning/foo.md]])")
        )
        self.assertTrue(
            _grounded_in_personal_raw("[[raw/origin-apple-notes/亲密关系.md]]")
        )
        self.assertTrue(
            _grounded_in_personal_raw("[[raw/_posts/new-apple-notes/2026-06-14.md]]")
        )
        self.assertTrue(_grounded_in_personal_raw("see raw/new-apple-notes/x.md"))

    def test_grounding_rejects_twitter_only(self):
        self.assertFalse(
            _grounded_in_personal_raw("(Source: [[raw/twitter/bookmarks.md]])")
        )

    def test_principle_requires_personal_raw_or_discovery(self):
        meta = {"level": 2, "confidence": 0.9, "tags": ["type/principle"]}
        self.assertTrue(
            _qualifies_principle(meta, "grounded in [[raw/_posts/diary/a.md]]")
        )
        self.assertTrue(_qualifies_principle(meta, "from discovery/2026-07-01.md"))
        self.assertFalse(
            _qualifies_principle(meta, "only [[raw/twitter/x.md]] bookmarks")
        )
        self.assertFalse(_qualifies_principle(meta, "no raw provenance at all"))

    def test_evolution_drops_distilled_noise(self):
        body = "Distilled from raw source [[raw/_posts/diary/a.md]]."
        self.assertTrue(_is_evolution_noise(body))
        self.assertFalse(_evolution_line_qualifies(body=body, is_shift=True))
        self.assertFalse(_evolution_line_qualifies(body=body, is_shift=False))

    def test_evolution_keeps_belief_change_signal(self):
        body = "Cognitive Shift: revised stance on vulnerability vs control."
        self.assertFalse(_is_evolution_noise(body))
        self.assertTrue(_evolution_line_qualifies(body=body, is_shift=False))

    def test_evolution_shift_page_non_noise_kept(self):
        body = "Merged overlapping leadership notes into one operating rule."
        self.assertTrue(_evolution_line_qualifies(body=body, is_shift=True))
        self.assertFalse(_evolution_line_qualifies(body=body, is_shift=False))


class TestTwinHypothesesAndCoexistence(unittest.TestCase):
    def test_parse_and_filter_hypotheses(self):
        blocks = _parse_hypothesis_blocks(SAMPLE_HYPOTHESES)
        self.assertEqual(len(blocks), 3)
        included = [b for b in blocks if _hypothesis_included(b)]
        ids = {b["id"] for b in included}
        self.assertEqual(ids, {"H-aaa", "H-bbb"})

    def test_collect_judged_from_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Self-Hypotheses.md"
            path.write_text(SAMPLE_HYPOTHESES, encoding="utf-8")
            items = _collect_judged_hypotheses(path=path)
            self.assertEqual({i["id"] for i in items}, {"H-aaa", "H-bbb"})

    def test_coexistence_signal(self):
        self.assertTrue(_has_coexistence_signal("两条话语同库并存，尚未合成"))
        self.assertFalse(_has_coexistence_signal("领导不必全知；容纳不确定"))


class TestTwinEssenceAndDedupe(unittest.TestCase):
    def test_near_duplicate_principles_fold(self):
        a = {
            "title": "先利益后逻辑",
            "rel": "wiki/a.md",
            "level": 2,
            "confidence": 0.84,
            "summary": "**Operating rule:** 先保护对方自尊与 self-interest 叙事，逻辑才进门；人对事实的反应常是对内在威胁的反应。",
            "tags": ["topic/leadership", "type/principle"],
            "last_updated": "2026-07-01",
        }
        b = {
            "title": "利益安全与真实领导",
            "rel": "wiki/b.md",
            "level": 2,
            "confidence": 0.82,
            "summary": "**Operating rule:** 先让对方在利益与自尊叙事里站稳，再暴露不确定与探询；策略性的「护自尊」若缺少真实与脆弱，会沦为操纵。",
            "tags": ["topic/leadership", "type/principle"],
            "last_updated": "2026-07-02",
        }
        c = {
            "title": "知识系统",
            "rel": "wiki/c.md",
            "level": 2,
            "confidence": 0.95,
            "summary": "**Operating rule:** 个人语料经 raw→wiki 复利 distillation；工具服务于可重复合成。",
            "tags": ["topic/systems", "type/principle"],
            "last_updated": "2026-07-03",
        }
        sim = _principle_affinity(a, b)
        self.assertGreaterEqual(sim, 0.30)
        kept = _dedupe_principles([a, b, c], threshold=0.30)
        rels = {p["rel"] for p in kept}
        self.assertIn("wiki/a.md", rels)
        self.assertIn("wiki/c.md", rels)
        self.assertNotIn("wiki/b.md", rels)
        related = kept[0]["related"] + kept[1]["related"]
        self.assertTrue(any(r["rel"] == "wiki/b.md" for r in related))

    def test_essence_is_not_build_stats(self):
        principles = [
            {
                "summary": "**Operating rule:** 领导不必全知；容纳不确定。",
                "tags": ["topic/leadership"],
                "confidence": 0.9,
            },
            {
                "summary": "**Operating rule:** 关系优先经营共同体验与连结。",
                "tags": ["topic/relationships"],
                "confidence": 0.9,
            },
        ]
        text = _build_essence(
            principles,
            coexistences=[
                {"summary": "两条话语同库并存，尚未合成一条可操作的桥接原则。"}
            ],
            tensions=[],
            hypotheses=[{"claim": "决策拖延，害怕承担责任。"}],
        )
        self.assertIn("核心原则", text)
        self.assertIn("最大张力", text)
        self.assertIn("已认账假设", text)
        self.assertNotIn("Full catalog", text)
        self.assertNotIn("principle(s)", text)


if __name__ == "__main__":
    unittest.main()
