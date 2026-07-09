"""Build a static HTML snapshot of self-wiki/ for Cloudflare Pages."""

from __future__ import annotations

import argparse
from urllib.parse import quote
import html
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from config import LOG_DIR, MEMEX_DIR, WORKSPACE_PATH, load_env
from memex.config import BACKLINKS_BLOCK
from memex.panels import render_panels
from memex.resolve import normalize_url, resolve_target
from site_theme import render_page, search_panel_html

logger = logging.getLogger(__name__)

VAULT_DIR = WORKSPACE_PATH / "self-wiki"
DEFAULT_OUT = WORKSPACE_PATH / "dist"
SKIP_DIR_NAMES = {"pending", "__pycache__", ".obsidian"}
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def vault_rel(path: Path) -> str:
    return path.relative_to(VAULT_DIR).as_posix()


def md_to_html_path(md_rel: str) -> str:
    if md_rel == "INDEX.md":
        return "index.html"
    path = Path(md_rel)
    if path.suffix.lower() == ".md":
        path = path.with_suffix(".html")
    return path.as_posix()


def _strip_agent_code_fence(text: str) -> str:
    """Remove accidental ```markdown wrapper from agent-written vault pages."""

    if not text.startswith("```"):
        return text
    first_line = text.split("\n", 1)[0].strip().lower()
    if first_line not in ("```markdown", "```md"):
        return text
    body = text.split("\n", 1)[1] if "\n" in text else ""
    body = re.sub(r"\n```\s*$", "", body)
    return body


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    text = _strip_agent_code_fence(text)
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    raw_fm = text[4:end]
    body = text[end + 5 :]
    try:
        meta = yaml.safe_load(raw_fm) or {}
    except (yaml.YAMLError, ValueError):
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def normalize_link_target(raw: str) -> str:
    from fix_provenance_links import canonical_wikilink_target

    target = canonical_wikilink_target(raw.split("|", 1)[0].strip())
    if target.startswith("wiki/") or target.startswith("raw/") or target.startswith(
        "twin/"
    ) or target.startswith("discovery/") or target.startswith("gap/") or target.startswith(
        "evolution/"
    ) or target.startswith("outputs/") or target.startswith("log/"):
        return target
    if target.endswith("/"):
        return target.rstrip("/")
    if "/" not in target and not target.endswith(".md"):
        return f"wiki/{target}.md"
    if not target.endswith(".md") and "." not in Path(target).name:
        return f"{target}.md"
    return target


def strip_backlinks_for_html(body: str) -> str:
    return BACKLINKS_BLOCK.sub("", body)


def load_memex_for_publish() -> dict | None:
    from memex.cache import load_memex_cache
    from memex.graph import build_memex_context
    from memex import state

    cached = load_memex_cache()
    pages = collect_markdown(VAULT_DIR)
    vault_pages = []
    for rel, path in pages.items():
        text = path.read_text(encoding="utf-8", errors="ignore")
        meta, body = _parse_frontmatter(text)
        from memex.sources import VaultPage, layer_and_section

        layer, section = layer_and_section(rel)
        vault_pages.append(
            VaultPage(
                rel=rel,
                path=path,
                title=str(meta.get("title") or Path(rel).stem),
                body=body,
                meta=meta,
                layer=layer,
                section=section,
            )
        )
    if cached:
        cached["pages_by_rel"] = {p.rel: p for p in vault_pages}
        cached["pages_by_url"] = {normalize_url(p.url): p for p in vault_pages}
        state.set_ctx(cached)
        return cached
    logger.warning("log/memex/graph.json missing — run `make ingest` first; rebuilding in memory")
    ctx = build_memex_context()
    state.set_ctx(ctx)
    return ctx


class VaultIndex:
    """Fallback basename resolver when memex cache unavailable."""

    def __init__(self, md_files: dict[str, Path]) -> None:
        self.md_files = md_files
        self.by_basename: dict[str, list[str]] = {}
        for rel in md_files:
            base = Path(rel).name
            self.by_basename.setdefault(base, []).append(rel)

    def resolve(self, raw_target: str) -> str | None:
        target = normalize_link_target(raw_target)
        if target in self.md_files:
            return md_to_html_path(target)
        base = Path(target).name
        if not base.endswith(".md"):
            base = f"{base}.md"
        matches = self.by_basename.get(base, [])
        if len(matches) == 1:
            return md_to_html_path(matches[0])
        if target.endswith(".md"):
            wiki_guess = f"wiki/{Path(target).name}"
            if wiki_guess in self.md_files:
                return md_to_html_path(wiki_guess)
        return None


def collect_markdown(vault: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in vault.rglob("*.md", recurse_symlinks=True):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        rel = vault_rel(path)
        files[rel] = path
    return files


def copy_static_assets(vault: Path, out: Path) -> int:
    copied = 0
    for path in vault.rglob("*", recurse_symlinks=True):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() == ".md":
            continue
        rel = vault_rel(path)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied += 1
    return copied


def render_inline(text: str, index: VaultIndex, ctx: dict | None = None) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"`([^`]+)`",
        r"<code>\1</code>",
        escaped,
    )

    def replace_wikilink(match: re.Match[str]) -> str:
        from fix_provenance_links import canonical_wikilink_target, wikilink_display_label

        raw = match.group(1)
        canonical = canonical_wikilink_target(raw)
        label = wikilink_display_label(raw)
        href = None
        if ctx:
            entry = resolve_target(
                canonical,
                ctx.get("registry", {}),
                fuzzy_lookup=ctx.get("fuzzy_lookup"),
                backlink_counts=ctx.get("backlink_counts"),
            )
            if entry:
                href = entry["url"].lstrip("/")
        if not href:
            href = index.resolve(canonical)
        safe_label = html.escape(html.unescape(label))
        if href:
            return f'<a href="/{href}" class="wikilink">{safe_label}</a>'
        return f'<span class="wikilink-missing">{safe_label}</span>'

    escaped = WIKILINK_RE.sub(replace_wikilink, escaped)
    return escaped


SOURCE_TRAIL_RE = re.compile(r"\(Source:\s*\[\[[^\]]+\]\]\)", re.IGNORECASE)
EPISTEMIC_SPLIT_RE = re.compile(
    r"(?=\s\*\*\[(?:Literal|AI Synthesis|Socratic Observation)\])"
)
INLINE_BULLET_SPLIT_RE = re.compile(r" (?=- )")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_CELL_RE = re.compile(r"^:?-{3,}:?$")


def _parse_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or "|" not in stripped[1:]:
        return None
    inner = stripped.strip("|")
    cells: list[str] = []
    current: list[str] = []
    i = 0
    in_wikilink = False
    while i < len(inner):
        ch = inner[i]
        if ch == "[" and i + 1 < len(inner) and inner[i + 1] == "[":
            in_wikilink = True
            current.append("[[")
            i += 2
            continue
        if in_wikilink and ch == "]" and i + 1 < len(inner) and inner[i + 1] == "]":
            in_wikilink = False
            current.append("]]")
            i += 2
            continue
        if ch == "|" and not in_wikilink:
            cells.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    cells.append("".join(current).strip())
    return cells


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(
        TABLE_SEP_CELL_RE.match(cell.replace(" ", "")) for cell in cells if cell
    )


def _render_table(
    rows: list[list[str]],
    index: VaultIndex,
    ctx: dict | None,
) -> str:
    if not rows:
        return ""
    header = rows[0]
    body_rows = [row for row in rows[1:] if not _is_separator_row(row)]
    parts = ["<table><thead><tr>"]
    for cell in header:
        parts.append(f"<th>{render_inline(cell, index, ctx)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in body_rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{render_inline(cell, index, ctx)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _split_source_trail(text: str) -> tuple[str, str]:
    """Detach trailing (Source: [[...]]) for a separate provenance line."""

    matches = list(SOURCE_TRAIL_RE.finditer(text))
    if not matches:
        return text.strip(), ""
    last = matches[-1]
    body = text[: last.start()].strip()
    source = last.group(0).strip()
    return body, source


def _split_epistemic_chunks(text: str) -> list[str]:
    chunks = [part.strip() for part in EPISTEMIC_SPLIT_RE.split(text) if part.strip()]
    return chunks or ([text.strip()] if text.strip() else [])


def _render_prose_line(
    stripped: str,
    index: VaultIndex,
    ctx: dict | None,
) -> list[str]:
    """Turn one markdown line into paragraphs, lists, and source lines."""

    body, source_trail = _split_source_trail(stripped)
    blocks: list[str] = []

    parts = INLINE_BULLET_SPLIT_RE.split(body)
    if len(parts) == 1:
        for chunk in _split_epistemic_chunks(body):
            blocks.append(f"<p>{render_inline(chunk, index, ctx)}</p>")
    else:
        intro = parts[0].strip()
        if intro:
            for chunk in _split_epistemic_chunks(intro):
                blocks.append(f"<p>{render_inline(chunk, index, ctx)}</p>")
        items = [part.strip() for part in parts[1:] if part.strip()]
        if items:
            lis: list[str] = []
            for item in items:
                item_body, _ = _split_source_trail(item)
                item_body = item_body.removeprefix("- ").strip()
                if item_body:
                    lis.append(f"<li>{render_inline(item_body, index, ctx)}</li>")
            if lis:
                blocks.append("<ul>" + "".join(lis) + "</ul>")

    if source_trail:
        blocks.append(
            f'<p class="source-line">{render_inline(source_trail, index, ctx)}</p>'
        )
    return blocks


def markdown_body_to_html(body: str, index: VaultIndex, ctx: dict | None = None) -> str:
    from memex.config import HTML_COMMENT_RE

    body = HTML_COMMENT_RE.sub("", body)
    blocks: list[str] = []
    in_list = False
    in_code = False
    in_table = False
    fence_lang = ""
    code_lines: list[str] = []
    table_rows: list[list[str]] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            blocks.append("</ul>")
            in_list = False

    def close_table() -> None:
        nonlocal in_table, table_rows
        if in_table:
            blocks.append(_render_table(table_rows, index, ctx))
            in_table = False
            table_rows = []

    def close_code_fence() -> None:
        nonlocal in_code, fence_lang, code_lines
        content = "\n".join(code_lines)
        if fence_lang == "mermaid":
            blocks.append(f'<pre class="mermaid">{content}</pre>')
        else:
            blocks.append(f"<pre><code>{html.escape(content)}</code></pre>")
        code_lines = []
        in_code = False
        fence_lang = ""

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                close_code_fence()
            else:
                close_list()
                close_table()
                in_code = True
                info = line.strip()[3:].strip().lower()
                fence_lang = info.split()[0] if info else ""
            continue
        if in_code:
            code_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            close_list()
            close_table()
            continue

        table_cells = _parse_table_row(stripped)
        if table_cells is not None:
            close_list()
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(table_cells)
            continue

        close_table()
        if stripped.startswith("#"):
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            text = stripped[level:].strip()
            heading_cls = ""
            if level == 3 and text.lower().startswith("distillation"):
                heading_cls = ' class="distillation-heading"'
            blocks.append(
                f"<h{level}{heading_cls}>{render_inline(text, index, ctx)}</h{level}>"
            )
        elif stripped.startswith(">"):
            close_list()
            blocks.append(
                f"<blockquote>{render_inline(stripped[1:].strip(), index, ctx)}</blockquote>"
            )
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{render_inline(stripped[2:].strip(), index, ctx)}</li>")
        else:
            close_list()
            blocks.extend(_render_prose_line(stripped, index, ctx))

    close_list()
    close_table()
    if in_code:
        close_code_fence()
    return "\n".join(blocks)


def page_html(
    title: str,
    body_html: str,
    *,
    rel_path: str,
    panels_html: str = "",
    with_search: bool = False,
) -> str:
    is_hub = rel_path == "INDEX.md"
    subtitle = "Personal second brain — raw, wiki, twin, and memex."
    extra = (search_panel_html() if with_search else "") + panels_html
    full_body = body_html + extra
    if is_hub:
        return render_page(
            title,
            full_body,
            rel_path=rel_path,
            hero_title="Self-Wiki",
            subtitle=subtitle,
            compact=False,
            with_search=with_search,
        )
    if not rel_path.endswith("index.html"):
        full_body = f"<h2>{html.escape(title)}</h2>\n{full_body}"
    return render_page(
        title,
        full_body,
        rel_path=rel_path,
        compact=True,
    )


def _all_directory_paths(md_files: dict[str, Path]) -> set[str]:
    dirs: set[str] = set()
    for rel in md_files:
        parts = Path(rel).parts[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add(Path(*parts[:i]).as_posix())
    return dirs


def _directory_children(dir_rel: str, md_files: dict[str, Path]) -> tuple[list[str], list[str]]:
    prefix = f"{dir_rel}/" if dir_rel else ""
    subdirs: set[str] = set()
    files: list[str] = []
    for rel in sorted(md_files):
        if dir_rel and not rel.startswith(prefix):
            continue
        rest = rel[len(prefix) :] if dir_rel else rel
        parts = Path(rest).parts
        if len(parts) == 1:
            files.append(rel)
        else:
            subdirs.add(parts[0])
    return sorted(subdirs), files


def directory_listing_html(dir_rel: str, subdirs: list[str], files: list[str]) -> str:
    rows = []
    for sub in subdirs:
        sub_path = f"{dir_rel}/{sub}" if dir_rel else sub
        rows.append(
            f'<a class="list-item" href="/{quote(sub_path, safe="/")}/index.html">'
            f"{html.escape(sub)}/"
            f"<small>{html.escape(sub_path)}/</small>"
            f"</a>"
        )
    for item in files:
        href = "/" + md_to_html_path(item)
        name = Path(item).stem
        rows.append(
            f'<a class="list-item" href="{href}">'
            f"{html.escape(name)}"
            f"<small>{html.escape(item)}</small>"
            f"</a>"
        )
    label = dir_rel or "self-wiki"
    body = f"<h2>{html.escape(label)}</h2>\n<div class=\"list\">{''.join(rows) or '<p>No pages.</p>'}</div>"
    return body


def write_directory_indexes(out: Path, md_files: dict[str, Path]) -> int:
    written = 0
    for dir_rel in sorted(_all_directory_paths(md_files)):
        subdirs, files = _directory_children(dir_rel, md_files)
        body = directory_listing_html(dir_rel, subdirs, files)
        dest = out / dir_rel / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            page_html(dir_rel, body, rel_path=f"{dir_rel}/index.html"),
            encoding="utf-8",
        )
        written += 1
    return written


def copy_bundled_static(out: Path) -> int:
    """Copy scripts/static/ assets (search.js, etc.) into dist/static/."""
    src_dir = Path(__file__).parent / "static"
    if not src_dir.is_dir():
        return 0
    copied = 0
    for path in src_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src_dir).as_posix()
        dest = out / "static" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied += 1
    return copied


def copy_memex_artifacts(out: Path, *, ctx: dict | None = None) -> int:
    copied = 0
    if not MEMEX_DIR.is_dir():
        return copied
    for name in ("search-index.json", "graph.json"):
        src = MEMEX_DIR / name
        if src.is_file():
            dest = out / "static" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1
    dest = out / "memex" / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if ctx:
        from memex.write_index import render_memex_index_html

        dest.write_text(render_memex_index_html(ctx), encoding="utf-8")
        copied += 1
    else:
        memex_index = MEMEX_DIR / "index.html"
        if memex_index.is_file():
            shutil.copy2(memex_index, dest)
            copied += 1
    return copied


def build_static_site(*, vault: Path = VAULT_DIR, out: Path = DEFAULT_OUT) -> dict[str, int]:
    if not vault.is_dir():
        raise FileNotFoundError(f"Vault not found: {vault}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    md_files = collect_markdown(vault)
    index = VaultIndex(md_files)
    ctx = load_memex_for_publish()
    html_count = 0

    for rel, path in sorted(md_files.items()):
        text = path.read_text(encoding="utf-8", errors="ignore")
        meta, body = _parse_frontmatter(text)
        title = str(meta.get("title") or Path(rel).stem)
        body = strip_backlinks_for_html(body)
        content = markdown_body_to_html(body, index, ctx)
        panels = ""
        if ctx:
            page = ctx.get("pages_by_rel", {}).get(rel)
            if page:
                panels = render_panels(page, ctx)
        page = page_html(
            title,
            content,
            rel_path=rel,
            panels_html=panels,
            with_search=(rel == "INDEX.md"),
        )
        dest = out / md_to_html_path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page, encoding="utf-8")
        html_count += 1

    redirects = out / "_redirects"
    redirects.write_text("/INDEX.html /index.html 301\n/INDEX /index.html 301\n", encoding="utf-8")

    dir_indexes = write_directory_indexes(out, md_files)
    assets = copy_static_assets(vault, out)
    bundled = copy_bundled_static(out)
    memex_artifacts = copy_memex_artifacts(out, ctx=ctx)

    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "pages": html_count,
        "assets": assets,
        "vault": str(vault),
    }
    (out / "_publish.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info(
        "Built %d HTML page(s), %d directory index(es), %d static asset(s), bundled=%d → %s",
        html_count,
        dir_indexes,
        assets,
        bundled,
        out,
    )
    return {
        "pages": html_count,
        "dir_indexes": dir_indexes,
        "assets": assets,
        "bundled_static": bundled,
        "memex_artifacts": memex_artifacts,
    }


def deploy_pages(out: Path, *, project: str, branch: str = "main") -> None:
    base = ["pages", "deploy", str(out), "--project-name", project, "--branch", branch]
    if shutil.which("wrangler"):
        cmd = ["wrangler", *base]
    elif shutil.which("npx"):
        cmd = ["npx", "wrangler", *base]
    else:
        raise RuntimeError("wrangler not found — install: npm i -g wrangler")
    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> int:
    load_env()
    parser = argparse.ArgumentParser(description="Build/deploy static self-wiki for Cloudflare Pages")
    parser.add_argument("--out", type=Path, default=Path(os.environ.get("PUBLISH_DIR", DEFAULT_OUT)))
    parser.add_argument("--vault", type=Path, default=VAULT_DIR)
    parser.add_argument("--deploy", action="store_true", help="Deploy with wrangler after build")
    parser.add_argument(
        "--project",
        default=os.environ.get("CLOUDFLARE_PAGES_PROJECT", "self-mirror"),
        help="Cloudflare Pages project name (production URL: https://<name>.pages.dev)",
    )
    parser.add_argument(
        "--branch",
        default=os.environ.get("CLOUDFLARE_PAGES_BRANCH", "main"),
        help="Cloudflare Pages deployment branch label",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    stats = build_static_site(vault=args.vault, out=args.out)

    deploy = args.deploy or os.environ.get("PUBLISH_DEPLOY", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if deploy:
        deploy_pages(args.out, project=args.project, branch=args.branch)
    else:
        logger.info("Build only (set PUBLISH_DEPLOY=1 or --deploy to upload)")
    print(json.dumps({"out": str(args.out), **stats}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
