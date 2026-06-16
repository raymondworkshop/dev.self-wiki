"""Incubate new L1 wiki themes from repeated no_actions compression signals."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from apply_ingest import apply_actions
from config import LOG_DIR, WORKSPACE_PATH
from lang_utils import detect_language
from models import WikiPage
from wiki_synth_manifest import (
    _file_hash,
    _raw_rel_from_compression,
    load_manifest,
    mark_done,
)
from wiki_themes import load_existing_themes

REPORT_JSON = LOG_DIR / "incubate_themes_report.json"

# Candidate NEW L1 bridge themes (skip if title already in wiki/)
CANDIDATE_THEMES: list[dict] = [
    {
        "title": "算法与数据结构学习",
        "description": "排序、搜索、树、哈希与复杂度直觉的复习笔记簇。",
        "keywords": [
            "algorithm",
            "sort",
            "binary search",
            "priority queue",
            "hash",
            "clustering",
            "tree",
            "数据结构",
            "算法",
            "complexity",
        ],
        "tags": ["type/synthesis", "topic/learning", "topic/engineering"],
    },
    {
        "title": "阅读与书摘笔记",
        "description": "读书摘要、作者观点与可迁移提醒的横向主题。",
        "keywords": [
            "读书",
            "reading",
            "book",
            "river town",
            "country driving",
            "frankl",
            "meaning",
            "书摘",
            "novel",
            "author",
        ],
        "tags": ["type/synthesis", "topic/reading"],
    },
    {
        "title": "幸福与意识探索",
        "description": "幸福、意识、心理学与人生意义相关的阅读与反思。",
        "keywords": [
            "happiness",
            "consciousness",
            "幸福",
            "意识",
            "psychology",
            "mind",
            "well-being",
            "anatomy of consciousness",
        ],
        "tags": ["type/synthesis", "topic/psychology", "topic/meaning"],
    },
    {
        "title": "工程实践与系统学习",
        "description": "SDK、系统、NLP、统计与工程笔记的横向桥接。",
        "keywords": [
            "android",
            "sdk",
            "system",
            "nlp",
            "statistics",
            "opencv",
            "engineering",
            "computer system",
            "facerecognition",
        ],
        "tags": ["type/synthesis", "topic/engineering", "topic/learning"],
    },
    {
        "title": "职业选择与成长策略",
        "description": "职业决策、晋升路径、机会判断与长期成长策略。",
        "keywords": [
            "选择",
            "决定",
            "decision",
            "choice",
            "career",
            "job",
            "interview",
            "offer",
            "promotion",
            "职场",
            "职业",
            "成长",
            "面试",
            "机会",
            "路径",
            "主动性",
            "agency",
            "事业",
        ],
        "tags": ["type/synthesis", "topic/career", "topic/strategy"],
    },
    {
        "title": "执行系统与习惯设计",
        "description": "目标拆解、复盘、节奏管理与习惯形成方法。",
        "keywords": [
            "habit",
            "routine",
            "todo",
            "review",
            "weekly",
            "复盘",
            "习惯",
            "执行",
            "计划",
            "节奏",
            "目标拆解",
        ],
        "tags": ["type/synthesis", "topic/execution", "topic/learning"],
    },
    {
        "title": "情绪调节与心理韧性",
        "description": "压力管理、情绪识别与恢复力提升相关实践。",
        "keywords": [
            "emotion",
            "stress",
            "anxiety",
            "burnout",
            "resilience",
            "情绪",
            "压力",
            "焦虑",
            "韧性",
            "恢复",
            "自我调节",
        ],
        "tags": ["type/synthesis", "topic/psychology", "topic/wellbeing"],
    },
    {
        "title": "产品思维与用户价值",
        "description": "围绕用户问题、价值验证与产品迭代的主题集合。",
        "keywords": [
            "product",
            "user",
            "feature",
            "iteration",
            "feedback",
            "产品",
            "用户",
            "需求",
            "价值",
            "迭代",
            "验证",
        ],
        "tags": ["type/synthesis", "topic/product", "topic/strategy"],
    },
    {
        "title": "写作表达与叙事能力",
        "description": "写作、表达、论证结构与叙事风格训练。",
        "keywords": [
            "writing",
            "essay",
            "narrative",
            "argument",
            "表达",
            "写作",
            "叙事",
            "观点",
            "结构",
            "文风",
        ],
        "tags": ["type/synthesis", "topic/communication", "topic/learning"],
    },
    {
        "title": "价值观与身份认同演化",
        "description": "价值观、身份叙事与自我定位随时间变化的主题。",
        "keywords": [
            "意义",
            "meaning",
            "identity",
            "values",
            "belief",
            "self",
            "价值观",
            "身份",
            "自我认同",
            "信念",
            "人生方向",
        ],
        "tags": ["type/synthesis", "topic/identity", "type/shift"],
    },
    {
        "title": "主动性与领导管理",
        "description": "主动选择、承担责任、领导与管理实践的交叉主题。",
        "keywords": [
            "主动性",
            "agency",
            "选择",
            "决定",
            "leadership",
            "management",
            "leader",
            "manage",
            "领导",
            "管理",
            "ownership",
            "responsibility",
            "决策",
            "事业",
        ],
        "tags": ["type/synthesis", "topic/leadership", "topic/agency"],
    },
    {
        "title": "关系边界与协作方式",
        "description": "关系中的边界设定、冲突协商与合作机制。",
        "keywords": [
            "关系",
            "爱情",
            "家庭",
            "朋友",
            "boundary",
            "conflict",
            "collaboration",
            "trust",
            "关系边界",
            "协作",
            "信任",
            "冲突",
            "界限",
            "合作方式",
        ],
        "tags": ["type/synthesis", "topic/relationship", "topic/communication"],
    },
    {
        "title": "亲密关系与家庭经营",
        "description": "围绕爱情、家庭与长期关系经营的经验与反思。",
        "keywords": [
            "关系",
            "爱情",
            "家庭",
            "朋友",
            "亲密",
            "伴侣",
            "婚姻",
            "家人",
            "love",
            "family",
            "friendship",
            "relationship",
        ],
        "tags": ["type/synthesis", "topic/relationship", "topic/family"],
    },
    {
        "title": "事业发展与工程实践",
        "description": "事业推进、工程执行与技术成长交织的主题。",
        "keywords": [
            "事业",
            "工程",
            "career",
            "engineering",
            "技术",
            "项目",
            "执行",
            "system",
            "实践",
            "成长",
            "leader",
            "management",
        ],
        "tags": ["type/synthesis", "topic/career", "topic/engineering"],
    },
    {
        "title": "学习方法与认知升级",
        "description": "学习策略、抽象能力与迁移能力提升的实践。",
        "keywords": [
            "learning",
            "mental model",
            "abstraction",
            "transfer",
            "study",
            "学习方法",
            "认知",
            "模型",
            "迁移",
            "抽象",
        ],
        "tags": ["type/synthesis", "topic/learning", "topic/cognition"],
    },
]


def _thresholds() -> dict[str, float | int]:
    return {
        "support_count": int(os.environ.get("INCUBATE_SUPPORT_COUNT", "3")),
        "mean_conf": float(os.environ.get("INCUBATE_MEAN_CONF", "0.78")),
        "max_conf": float(os.environ.get("INCUBATE_MAX_CONF", "0.82")),
        "min_file_conf": float(os.environ.get("INCUBATE_MIN_FILE_CONF", "0.75")),
    }


def _body_only(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            return text[end + 3 :]
    return text


def _excerpt(body: str, max_chars: int = 500) -> str:
    body = _body_only(body)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.startswith("#")]
    parts: list[str] = []
    n = 0
    for ln in lines:
        if ln.startswith(">"):
            parts.append(ln)
        if n + len(ln) > max_chars:
            break
        if not ln.startswith(">"):
            parts.append(ln)
        n += len(ln)
    return " ".join(parts[:6]) or body[:max_chars]


def score_candidate(text: str, keywords: list[str]) -> tuple[int, float]:
    """Return (hit_count, confidence) for one compression body vs candidate keywords."""

    lower = text.lower()
    hits = sum(1 for k in keywords if k.lower() in lower)
    if hits == 0:
        return 0, 0.0
    conf = min(0.95, 0.68 + 0.04 * hits)
    return hits, round(conf, 2)


def list_no_action_files() -> list[tuple[str, Path]]:
    data = load_manifest()
    out: list[tuple[str, Path]] = []
    for comp_rel, entry in sorted(data.get("files", {}).items()):
        if entry.get("status") != "no_actions":
            continue
        abs_path = WORKSPACE_PATH / comp_rel
        if not abs_path.is_file():
            resolved = abs_path.resolve()
            if resolved.is_file():
                abs_path = resolved
            else:
                continue
        if "compression/twitter/" in comp_rel.replace("\\", "/"):
            continue
        out.append((comp_rel, abs_path))
    return out


@dataclass
class FileMatch:
    comp_rel: str
    abs_path: Path
    confidence: float
    hits: int


@dataclass
class ThemeCluster:
    title: str
    candidate: dict
    files: list[FileMatch] = field(default_factory=list)

    @property
    def support_count(self) -> int:
        return len(self.files)

    @property
    def mean_conf(self) -> float:
        if not self.files:
            return 0.0
        return sum(f.confidence for f in self.files) / len(self.files)

    @property
    def max_conf(self) -> float:
        if not self.files:
            return 0.0
        return max(f.confidence for f in self.files)

    def passes(self, t: dict[str, float | int]) -> bool:
        return (
            self.support_count >= int(t["support_count"])
            and self.mean_conf >= float(t["mean_conf"])
            and self.max_conf >= float(t["max_conf"])
        )


def build_clusters() -> tuple[list[ThemeCluster], dict[str, float | int]]:
    _, title_to_path = load_existing_themes()
    existing = set(title_to_path.keys())
    thresholds = _thresholds()
    min_file = float(thresholds["min_file_conf"])

    candidates = [c for c in CANDIDATE_THEMES if c["title"] not in existing]
    clusters: dict[str, ThemeCluster] = {
        c["title"]: ThemeCluster(title=c["title"], candidate=c) for c in candidates
    }

    for comp_rel, abs_path in list_no_action_files():
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        best_title = ""
        best_hits = 0
        best_conf = 0.0
        for cand in candidates:
            hits, conf = score_candidate(text, cand["keywords"])
            if conf >= min_file and (hits > best_hits or (hits == best_hits and conf > best_conf)):
                best_hits, best_conf, best_title = hits, conf, cand["title"]
        if best_title and best_conf >= min_file:
            clusters[best_title].files.append(
                FileMatch(comp_rel=comp_rel, abs_path=abs_path, confidence=best_conf, hits=best_hits)
            )

    passing = [c for c in clusters.values() if c.passes(thresholds)]
    passing.sort(key=lambda c: (-c.support_count, -c.mean_conf))
    return passing, thresholds


def _create_theme_page(cluster: ThemeCluster) -> WikiPage:
    cand = cluster.candidate
    page = WikiPage.create_new(cand["title"], level=1)
    lang = detect_language(cand["description"])
    if lang == "Chinese":
        summary = (
            f"> [AI Synthesis] 由 {cluster.support_count} 份压缩摘要交叉孵化的新 L1 主题"
            f"（mean conf {cluster.mean_conf:.2f}，max {cluster.max_conf:.2f}）。"
        )
    else:
        summary = (
            f"> [AI Synthesis] New L1 theme incubated from {cluster.support_count} compression digests "
            f"(mean conf {cluster.mean_conf:.2f}, max {cluster.max_conf:.2f})."
        )
    page.summary = summary.lstrip("> ").strip()
    page.front_matter["description"] = cand["description"]
    page.front_matter["confidence"] = round(cluster.mean_conf, 2)
    page.front_matter["confidence_rationale"] = (
        f"Cross-file incubation: support={cluster.support_count}, "
        f"mean={cluster.mean_conf:.2f}, max={cluster.max_conf:.2f}"
    )
    page.front_matter["tags"] = list(cand.get("tags", ["type/synthesis"]))
    page.body = "## Core patterns\n\n- _(Incubated; evidence appended below.)_\n"
    page.evolution = (
        f"- {datetime.now().strftime('%Y-%m-%d')}: Theme incubated from "
        f"{cluster.support_count} compression file(s) (threshold: support≥{_thresholds()['support_count']}, "
        f"mean≥{_thresholds()['mean_conf']}, max≥{_thresholds()['max_conf']})."
    )
    page.save()
    return page


def incubate(*, dry_run: bool = False, post_ingest: bool = False) -> dict:
    passing, thresholds = build_clusters()
    report: dict = {
        "generated_at": datetime.now().isoformat(),
        "thresholds": thresholds,
        "candidates_passing": len(passing),
        "themes_created": [],
        "dry_run": dry_run,
    }

    for cluster in passing:
        theme_entry = {
            "title": cluster.title,
            "support_count": cluster.support_count,
            "mean_conf": round(cluster.mean_conf, 3),
            "max_conf": round(cluster.max_conf, 3),
            "files": [f.comp_rel for f in cluster.files],
        }
        if dry_run:
            report["themes_created"].append(theme_entry)
            continue

        _create_theme_page(cluster)
        pages_linked = 0
        for fm in cluster.files:
            raw_suffix = _raw_rel_from_compression(fm.comp_rel)
            excerpt = _excerpt(fm.abs_path.read_text(encoding="utf-8", errors="replace"))
            payload = {
                "actions": [
                    {
                        "target_title": cluster.title,
                        "confidence_score": fm.confidence,
                        "confidence_rationale": f"Incubation keyword hits={fm.hits}",
                        "level": 1,
                        "summary": cluster.candidate["description"],
                        "description": "Incubation distillation",
                        "new_body_content": excerpt,
                        "tags": ["type/synthesis", "agent/incubate"],
                    }
                ]
            }
            pages_linked += apply_actions(payload, rel_path=raw_suffix)
            mark_done(fm.comp_rel, pages=1, content_hash=_file_hash(fm.abs_path))

        theme_entry["pages_linked"] = pages_linked
        report["themes_created"].append(theme_entry)

    if not dry_run:
        REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if post_ingest:
            import subprocess
            import sys

            subprocess.run(
                [sys.executable, str(Path(__file__).parent / "cli.py"), "post-ingest"],
                check=True,
                cwd=str(WORKSPACE_PATH),
            )

    return report


def print_report(report: dict) -> None:
    t = report["thresholds"]
    print(
        f"Incubate themes (support>={t['support_count']}, mean>={t['mean_conf']}, "
        f"max>={t['max_conf']}, min_file>={t['min_file_conf']})"
    )
    print(f"  passing clusters: {report['candidates_passing']}")
    for item in report.get("themes_created", []):
        print(
            f"  - {item['title']}: n={item['support_count']} "
            f"mean={item['mean_conf']} max={item['max_conf']} files={len(item.get('files', []))}"
        )
    if report.get("dry_run"):
        print("  (dry-run — no wiki writes)")
    elif REPORT_JSON.exists():
        print(f"  report: {REPORT_JSON.relative_to(WORKSPACE_PATH)}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Incubate new L1 wiki themes from no_actions clusters")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--post-ingest", action="store_true")
    args = p.parse_args(argv)
    report = incubate(dry_run=args.dry_run, post_ingest=args.post_ingest)
    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
