"""Composer-style wiki batch: 10 files, heuristic theme match, apply, no external LLM."""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from composer_wiki_batch import apply_batch_file, list_next
from config import WORKSPACE_PATH

# (wiki title, trigger keywords in raw text — any hit scores)
THEME_TRIGGERS: list[tuple[str, list[str]]] = [
    ("商业算盘与激励", ["市场", "激励", "交易费用", "产权", "economics", "商业", "钞票投票", "公司原理"]),
    ("公民话语与职场策略", ["中国", "社会", "职场", "政策", "民主", "宏观", "微观", "country driving", "尋路"]),
    ("连结式关系", ["关系", "友谊", "亲密", "friendship", "人际", "送禮", "建立關係"]),
    ("Communication", ["沟通", "communication", "冲突", "倾听", "validation", "I-statement"]),
    ("先利益后逻辑", ["利益", "自尊", "逻辑", "说服", "复述", "on-people"]),
    ("脆弱性领导", ["脆弱", "领导", "vulnerability", "leader", "坦诚", "诚实"]),
    ("能量与注意力账本", ["注意力", "能量", "专注", "burnout", "休息"]),
    ("知识系统与自我维基", ["wiki", "知识系统", "思考的技术", "思考", "学习", "memex", "second brain", "self-wiki"]),
    ("绽放与个性化路径", ["意义", "frankl", "活出生命", "meaning", "成长", "个性化", "绽放"]),
    ("Leadership and Management", ["管理", "executive", "领导", "团队", "performance", "mentor", "downward"]),
    ("Self-Perception and Validation", ["自尊", "validation", "自我", "争表现", "culture", "文化"]),
    ("Friendship", ["friend", "友谊", "朋友", "toxic"]),
]

SKIP_RE = re.compile(
    r"algorithm|sort|binary search|hash|clustering|priority.?queue|opencv|"
    r"logic.?gate|nlp|statistics|android sdk|computer system|facerecognition|"
    r"mcc_lsh|similaritysearch|hello.?world|part-\d{3}\.md|"
    r"topic/mathematics|topic/algorithms|topic/computer",
    re.I,
)
MIN_SCORE = 3


def _body_only(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            return text[end + 3 :]
    return text


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return ""


def _score(text: str) -> list[tuple[str, int]]:
    scores: list[tuple[str, int]] = []
    for title, keys in THEME_TRIGGERS:
        hits = sum(1 for k in keys if k.lower() in text)
        if hits:
            scores.append((title, hits))
    return sorted(scores, key=lambda x: x[1], reverse=True)


def _excerpt(body: str, max_chars: int = 600) -> str:
    body = _body_only(body)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    out: list[str] = []
    n = 0
    for ln in lines:
        if ln.startswith("#"):
            continue
        if n + len(ln) > max_chars:
            break
        out.append(ln)
        n += len(ln)
    return " ".join(out[:8]) or body[:max_chars]


def _action(raw_rel: str, title: str, body: str, score: int) -> dict:
    raw_link = raw_rel.replace("self-wiki/", "")
    if not raw_link.startswith("raw/"):
        raw_link = f"raw/{raw_link.lstrip('/')}"
    conf = min(0.92, 0.65 + 0.05 * score)
    excerpt = _excerpt(body)
    lang_zh = bool(re.search(r"[\u4e00-\u9fff]", body))
    if lang_zh:
        summary = f"从该 raw 笔记中提炼与「{title}」相关的模式（置信度 {conf:.2f}）。"
        content = f"{excerpt} (Source: [[{raw_link}]])"
    else:
        summary = f"Pattern from raw note relevant to [[{title}]] (confidence {conf:.2f})."
        content = f"{excerpt} (Source: [[{raw_link}]])"
    return {
        "target_title": title,
        "confidence_score": round(conf, 2),
        "confidence_rationale": f"Keyword/theme match score {score} in raw source.",
        "level": 1,
        "summary": summary,
        "description": f"Distillation from {raw_link}",
        "new_body_content": content,
        "tags": ["type/synthesis", "agent/composer-batch"],
    }


def build_batch(limit: int = 10, *, folder: str | None = None) -> dict:
    files: list[dict] = []
    for raw_rel in list_next(limit, folder=folder):
        abs_path = WORKSPACE_PATH / raw_rel
        if not abs_path.is_file():
            abs_path = abs_path.resolve()
        body = _text(abs_path)
        if not body:
            files.append({"raw_path": raw_rel, "no_actions": True})
            continue
        stem = abs_path.name.lower()
        if SKIP_RE.search(stem) or SKIP_RE.search(body[:800]):
            files.append({"raw_path": raw_rel, "no_actions": True})
            continue
        ranked = _score(body)
        if not ranked or ranked[0][1] < MIN_SCORE:
            files.append({"raw_path": raw_rel, "no_actions": True})
            continue
        top_title, top_score = ranked[0]
        raw_body = abs_path.read_text(encoding="utf-8", errors="replace")
        files.append(
            {
                "raw_path": raw_rel,
                "actions": [_action(raw_rel, top_title, raw_body, top_score)],
            }
        )
    return {"files": files, "generated_at": datetime.now().isoformat()}


def run_loop(
    *,
    batch_size: int = 10,
    pause_seconds: float = 6.0,
    max_batches: int | None = None,
    folder: str | None = None,
) -> None:
    from wiki_synth_manifest import list_resume_targets

    batch_n = 0
    while list_resume_targets(folder=folder):
        if max_batches is not None and batch_n >= max_batches:
            break
        batch_n += 1
        data = build_batch(batch_size, folder=folder)
        pending_path = WORKSPACE_PATH / "self-wiki/log/pending" / f"composer-auto-batch-{batch_n:04d}.json"
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        stats = apply_batch_file(pending_path)
        applied = stats.get("applied", 0)
        pages = stats.get("pages", 0)
        no_actions = stats.get("no_actions", 0)
        print(
            f"Batch {batch_n}: applied={applied} pages={pages} no_actions={no_actions} "
            f"remaining≈{len(list_resume_targets(folder=folder))}",
            flush=True,
        )
        if pause_seconds > 0 and list_resume_targets(folder=folder):
            time.sleep(pause_seconds)

    # trust layer once at end
    import subprocess

    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "cli.py"), "ingest"],
        check=True,
        cwd=str(WORKSPACE_PATH),
    )
    print("Done. ingest complete.", flush=True)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--pause", type=float, default=6.0)
    p.add_argument("--max-batches", type=int, default=None)
    p.add_argument("--folder", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.dry_run:
        print(json.dumps(build_batch(args.batch_size, folder=args.folder), indent=2, ensure_ascii=False))
    else:
        run_loop(
            batch_size=args.batch_size,
            pause_seconds=args.pause,
            max_batches=args.max_batches,
            folder=args.folder,
        )
