"""Composer wiki-synthesize batch: apply actions JSON, mark manifest, list next N."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from apply_ingest import apply_actions
from config import WORKSPACE_PATH
from wiki_synth_manifest import (
    _file_hash,
    canonical_raw_rel,
    list_resume_targets,
    mark_done,
    raw_rel_inner,
)


def apply_batch_file(batch_path: Path) -> dict:
    data = json.loads(batch_path.read_text(encoding="utf-8"))
    stats = {"applied": 0, "pages": 0, "no_actions": 0, "errors": []}

    for entry in data.get("files", []):
        raw_path = entry.get("raw_path", "")
        if not raw_path:
            continue
        raw_rel = canonical_raw_rel(raw_path)
        abs_raw = WORKSPACE_PATH / raw_rel
        if not abs_raw.is_file():
            resolved = abs_raw.resolve()
            if resolved.is_file():
                abs_raw = resolved
            else:
                stats["errors"].append({"raw_path": raw_rel, "error": "not_found"})
                continue
        content_hash = _file_hash(abs_raw)
        raw_suffix = raw_rel_inner(raw_rel)

        if entry.get("no_actions"):
            mark_done(raw_rel, pages=0, content_hash=content_hash)
            stats["no_actions"] += 1
            continue

        actions = entry.get("actions", [])
        if not actions:
            mark_done(raw_rel, pages=0, content_hash=content_hash)
            stats["no_actions"] += 1
            continue

        try:
            payload = {
                "raw_path": raw_rel,
                "actions": actions,
            }
            pages = apply_actions(payload, rel_path=raw_suffix)
            mark_done(raw_rel, pages=pages, content_hash=content_hash)
            stats["applied"] += 1
            stats["pages"] += pages
        except Exception as exc:
            stats["errors"].append({"raw_path": raw_rel, "error": str(exc)})

    return stats


def list_next(limit: int, *, folder: str | None = None, wave: str | None = None) -> list[str]:
    targets = list_resume_targets(folder=folder, wave=wave)
    return [rel for rel, _ in targets[:limit]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Composer wiki-synthesize batch helper")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="Print next N pending raw paths")
    p_list.add_argument("--limit", type=int, default=10)
    p_list.add_argument("--folder")
    p_list.add_argument("--wave")
    p_list.set_defaults(func=lambda a: print("\n".join(list_next(a.limit, folder=a.folder, wave=a.wave))) or 0)

    p_apply = sub.add_parser("apply", help="Apply composer batch JSON")
    p_apply.add_argument("batch", help="Path to batch JSON with files[]")
    p_apply.set_defaults(
        func=lambda a: (
            print(json.dumps(apply_batch_file(Path(a.batch)), indent=2)) or 0
        )
    )

    p_stats = sub.add_parser("stats", help="Manifest summary")
    p_stats.set_defaults(
        func=lambda a: (
            print(json.dumps(__import__("wiki_synth_manifest").load_manifest().get("summary", {}), indent=2)) or 0
        )
    )

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
