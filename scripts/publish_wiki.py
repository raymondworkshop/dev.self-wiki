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

from config import WORKSPACE_PATH, load_env
from site_theme import render_page

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


def _parse_frontmatter(text: str) -> tuple[dict, str]:
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
    target = raw.split("|", 1)[0].strip()
    for prefix in (
        "self-wiki/",
        "../",
        "./",
    ):
        if target.startswith(prefix):
            target = target.removeprefix(prefix)
    if target.startswith("wiki/") or target.startswith("raw/") or target.startswith(
        "compression/"
    ) or target.startswith("twin/") or target.startswith("discovery/") or target.startswith(
        "gap/"
    ) or target.startswith("evolution/") or target.startswith("outputs/") or target.startswith(
        "log/"
    ):
        return target
    if target.endswith("/"):
        return target.rstrip("/")
    if "/" not in target and not target.endswith(".md"):
        return f"wiki/{target}.md"
    if not target.endswith(".md") and "." not in Path(target).name:
        return f"{target}.md"
    return target


class VaultIndex:
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
    for path in vault.rglob("*.md"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        rel = vault_rel(path)
        files[rel] = path
    return files


def copy_static_assets(vault: Path, out: Path) -> int:
    copied = 0
    for path in vault.rglob("*"):
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


def render_inline(text: str, index: VaultIndex) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"`([^`]+)`",
        r"<code>\1</code>",
        escaped,
    )

    def replace_wikilink(match: re.Match[str]) -> str:
        raw = html.unescape(match.group(1))
        label = raw.split("|", 1)[1].strip() if "|" in raw else raw.split("|", 1)[0].strip()
        href = index.resolve(raw)
        safe_label = html.escape(label)
        if href:
            return f'<a href="/{href}">{safe_label}</a>'
        return f"<code>[[{safe_label}]]</code>"

    escaped = WIKILINK_RE.sub(replace_wikilink, escaped)
    return escaped


def markdown_body_to_html(body: str, index: VaultIndex) -> str:
    blocks: list[str] = []
    in_list = False
    in_code = False
    fence_lang = ""
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            blocks.append("</ul>")
            in_list = False

    def close_code_fence() -> None:
        nonlocal in_code, fence_lang, code_lines
        content = html.escape("\n".join(code_lines))
        if fence_lang == "mermaid":
            blocks.append(f'<pre class="mermaid">{content}</pre>')
        else:
            blocks.append(f"<pre><code>{content}</code></pre>")
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
            continue
        if stripped.startswith("#"):
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            text = stripped[level:].strip()
            blocks.append(f"<h{level}>{render_inline(text, index)}</h{level}>")
        elif stripped.startswith(">"):
            close_list()
            blocks.append(
                f"<blockquote>{render_inline(stripped[1:].strip(), index)}</blockquote>"
            )
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{render_inline(stripped[2:].strip(), index)}</li>")
        else:
            close_list()
            blocks.append(f"<p>{render_inline(stripped, index)}</p>")

    close_list()
    if in_code:
        close_code_fence()
    return "\n".join(blocks)


def page_html(title: str, body_html: str, *, rel_path: str) -> str:
    is_hub = rel_path == "INDEX.md"
    subtitle = "Personal second brain — raw, compression, wiki, twin."
    if is_hub:
        return render_page(
            title,
            body_html,
            rel_path=rel_path,
            hero_title="Self-Wiki",
            subtitle=subtitle,
            compact=False,
        )
    if not rel_path.endswith("index.html"):
        body_html = f"<h2>{html.escape(title)}</h2>\n{body_html}"
    return render_page(
        title,
        body_html,
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


def build_static_site(*, vault: Path = VAULT_DIR, out: Path = DEFAULT_OUT) -> dict[str, int]:
    if not vault.is_dir():
        raise FileNotFoundError(f"Vault not found: {vault}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    md_files = collect_markdown(vault)
    index = VaultIndex(md_files)
    html_count = 0

    for rel, path in sorted(md_files.items()):
        text = path.read_text(encoding="utf-8", errors="ignore")
        meta, body = _parse_frontmatter(text)
        title = str(meta.get("title") or Path(rel).stem)
        content = markdown_body_to_html(body, index)
        page = page_html(title, content, rel_path=rel)
        dest = out / md_to_html_path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page, encoding="utf-8")
        html_count += 1

    redirects = out / "_redirects"
    redirects.write_text("/INDEX.html /index.html 301\n/INDEX /index.html 301\n", encoding="utf-8")

    dir_indexes = write_directory_indexes(out, md_files)
    assets = copy_static_assets(vault, out)

    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "pages": html_count,
        "assets": assets,
        "vault": str(vault),
    }
    (out / "_publish.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info(
        "Built %d HTML page(s), %d directory index(es), %d static asset(s) → %s",
        html_count,
        dir_indexes,
        assets,
        out,
    )
    return {"pages": html_count, "dir_indexes": dir_indexes, "assets": assets}


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
