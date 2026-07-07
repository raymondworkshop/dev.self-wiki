#!/usr/bin/env python3
"""CLI for self-wiki memex: inspect links, find gaps."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from memex import state
from memex.cache import load_memex_cache
from memex.graph import build_memex_context
from memex.queries import (
    find_missing_links,
    get_backlinks,
    get_contradicts,
    get_orphans,
    get_outgoing,
    get_top_linked,
)
from memex.resolve import normalize_url, resolve_candidates
from memex.sources import collect_vault_pages


def load_context(*, rebuild: bool = False) -> dict:
    if not rebuild:
        cached = load_memex_cache()
        if cached:
            pages = collect_vault_pages()
            cached["pages_by_rel"] = {p.rel: p for p in pages}
            cached["pages_by_url"] = {normalize_url(p.url): p for p in pages}
            state.set_ctx(cached)
            return cached
    ctx = build_memex_context()
    state.set_ctx(ctx)
    return ctx


def cmd_stats(ctx: dict) -> None:
    stats = ctx.get("stats", {})
    print(f"Files:     {stats.get('files', 0)}")
    print(f"Pages:     {stats.get('pages', 0)}")
    print(f"Wikilinks: {stats.get('wikilinks', 0)}")
    print(f"Missing:   {len(find_missing_links(ctx))}")
    print(f"Orphans:   {len(get_orphans(ctx))}")


def cmd_resolve(ctx: dict, target: str) -> None:
    candidates = resolve_candidates(
        target,
        ctx["registry"],
        fuzzy_lookup=ctx.get("fuzzy_lookup"),
        backlink_counts=ctx.get("backlink_counts"),
        return_all=True,
    )
    if not candidates:
        print(f"Unresolved: {target!r}")
        return
    for entry, score, label in candidates[:10]:
        print(f"  {score:3d}  {entry['title']}  {entry['url']}  ({label})")


def cmd_backlinks(ctx: dict, query: str) -> None:
    page = _find_page(ctx, query)
    if not page:
        return
    for item in get_backlinks(page, ctx):
        print(f"  {item['title']}  {item['url']}")
    typed = ctx.get("typed_backlinks", {}).get(normalize_url(page.url), {})
    for rel_type, items in typed.items():
        if items:
            print(f"\n{rel_type}:")
            for item in items:
                print(f"  {item['title']}  {item['url']}")


def cmd_outgoing(ctx: dict, query: str) -> None:
    page = _find_page(ctx, query)
    if not page:
        return
    for item in get_outgoing(page, ctx):
        print(f"  {item['title']}  {item['url']}")


def _find_page(ctx: dict, query: str):
    candidates = resolve_candidates(
        query,
        ctx["registry"],
        fuzzy_lookup=ctx.get("fuzzy_lookup"),
        return_all=True,
    )
    if not candidates:
        print(f"No page matched: {query!r}", file=sys.stderr)
        return None
    url = normalize_url(candidates[0][0]["url"])
    page = ctx.get("pages_by_url", {}).get(url)
    if not page:
        print(f"Page not in vault: {query!r}", file=sys.stderr)
    return page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self-wiki memex CLI")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild graph instead of cache")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("stats", help="Graph statistics")
    sub.add_parser("missing", help="Unresolved wikilinks")
    sub.add_parser("orphans", help="Pages with zero backlinks")
    p_top = sub.add_parser("top", help="Most-linked pages")
    p_top.add_argument("-n", type=int, default=15)
    sub.add_parser("contradicts", help="Contradicts edges")
    p_resolve = sub.add_parser("resolve", help="Resolve a wikilink target")
    p_resolve.add_argument("target")
    p_bl = sub.add_parser("backlinks", help="Backlinks for a page")
    p_bl.add_argument("page")
    p_out = sub.add_parser("outgoing", help="Outgoing links from a page")
    p_out.add_argument("page")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    ctx = load_context(rebuild=args.rebuild)

    if args.command == "stats":
        cmd_stats(ctx)
    elif args.command == "missing":
        for item in find_missing_links(ctx):
            print(f"{item['source']}: [[{item['target']}]]")
    elif args.command == "orphans":
        for item in get_orphans(ctx):
            print(f"{item['title']}  {item['url']}")
    elif args.command == "top":
        for item in get_top_linked(ctx, args.n):
            print(f"{item['count']:3d}  {item['title']}  {item['url']}")
    elif args.command == "contradicts":
        for item in get_contradicts(ctx):
            print(f"{item['source_title']} contradicts {item['target_title']}")
    elif args.command == "resolve":
        cmd_resolve(ctx, args.target)
    elif args.command == "backlinks":
        cmd_backlinks(ctx, args.page)
    elif args.command == "outgoing":
        cmd_outgoing(ctx, args.page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
