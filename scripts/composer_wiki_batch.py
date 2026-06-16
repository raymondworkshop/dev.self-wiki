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
    _comp_rel,
    _file_hash,
    _raw_rel_from_compression,
    list_resume_targets,
    mark_done,
    load_manifest,
    save_manifest,
)


def _raw_rel_from_comp_path(comp_path: str) -> str:
    rel = comp_path.replace("\\", "/")
    if rel.startswith("self-wiki/compression/"):
        rel = rel[len("self-wiki/compression/") :]
    return _raw_rel_from_compression(f"self-wiki/compression/{rel}")


def apply_batch_file(batch_path: Path) -> dict:
    data = json.loads(batch_path.read_text(encoding="utf-8"))
    stats = {"applied": 0, "pages": 0, "no_actions": 0, "errors": []}

    for entry in data.get("files", []):
        comp_path = entry.get("compression_path", "")
        if not comp_path:
            continue
        abs_comp = WORKSPACE_PATH / comp_path
        if not abs_comp.is_file():
            abs_comp = WORKSPACE_PATH / "self-wiki" / comp_path.lstrip("self-wiki/")
        comp_rel = _comp_rel(abs_comp) if abs_comp.is_file() else comp_path
        content_hash = _file_hash(abs_comp) if abs_comp.is_file() else ""
        raw_suffix = _raw_rel_from_comp_path(comp_rel).replace("raw/", "")

        if entry.get("no_actions"):
            mark_done(comp_rel, pages=0, content_hash=content_hash)
            stats["no_actions"] += 1
            continue

        actions = entry.get("actions", [])
        if not actions:
            mark_done(comp_rel, pages=0, content_hash=content_hash)
            stats["no_actions"] += 1
            continue

        try:
            payload = {
                "compression_path": comp_rel,
                "raw_path": _raw_rel_from_comp_path(comp_rel),
                "actions": actions,
            }
            pages = apply_actions(payload, rel_path=raw_suffix)
            mark_done(comp_rel, pages=pages, content_hash=content_hash)
            stats["applied"] += 1
            stats["pages"] += pages
        except Exception as exc:
            stats["errors"].append({"compression_path": comp_rel, "error": str(exc)})

    return stats


def list_next(limit: int, *, folder: str | None = None, wave: str | None = None) -> list[str]:
    targets = list_resume_targets(folder=folder, wave=wave)
    return [rel for rel, _ in targets[:limit]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Composer wiki-synthesize batch helper")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="Print next N pending compression paths")
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
            print(json.dumps(load_manifest().get("summary", {}), indent=2)) or 0
        )
    )

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
