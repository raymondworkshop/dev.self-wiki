"""Collect and parse vault markdown sources for memex."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from config import LOG_DIR, WORKSPACE_PATH
from memex.config import BACKLINKS_BLOCK, SKIP_DIR_NAMES

VAULT_DIR = WORKSPACE_PATH / "self-wiki"
MEMEX_DIR = LOG_DIR / "memex"

DATED_STEM_SUFFIX = re.compile(r"^(.+)-\d{4}-\d{2}-\d{2}$")


@dataclass
class VaultPage:
    rel: str
    path: Path
    title: str
    body: str
    meta: dict[str, Any] = field(default_factory=dict)
    layer: str = ""
    section: str = ""

    @property
    def url(self) -> str:
        if self.rel == "INDEX.md":
            return "/index.html"
        p = Path(self.rel)
        if p.suffix.lower() == ".md":
            p = p.with_suffix(".html")
        return "/" + p.as_posix()

    @property
    def stem(self) -> str:
        return Path(self.rel).stem


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    try:
        meta = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[end + 5 :]


def strip_backlinks_block(body: str) -> str:
    return BACKLINKS_BLOCK.sub("", body)


def strip_markdown(text: str) -> str:
    from memex.config import WIKILINK_PATTERN

    text = WIKILINK_PATTERN.sub(lambda m: m.group(1).split("|", 1)[0], text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`]", "", text)
    return text


def get_excerpt(page: VaultPage, max_len: int = 200) -> str:
    plain = strip_markdown(strip_backlinks_block(page.body))
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= max_len:
        return plain
    return plain[: max_len - 1].rstrip() + "…"


def vault_rel(path: Path) -> str:
    return path.relative_to(VAULT_DIR).as_posix()


def layer_and_section(rel: str) -> tuple[str, str]:
    parts = Path(rel).parts
    layer = parts[0] if parts else ""
    section = "/".join(parts[:2]) if len(parts) >= 2 else layer
    return layer, section


def is_vault_index(page: VaultPage) -> bool:
    return page.rel == "INDEX.md"


def is_layer_hub(page: VaultPage) -> bool:
    return page.rel.endswith("/index.md") or page.rel.endswith("/INDEX.md")


def layer_hub_url(layer: str) -> str:
    return f"/{layer}/index.html"


def collect_vault_pages() -> list[VaultPage]:
    pages: list[VaultPage] = []
    if not VAULT_DIR.is_dir():
        return pages
    for path in sorted(VAULT_DIR.rglob("*.md", recurse_symlinks=True)):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        rel = vault_rel(path)
        if rel.startswith("log/pending/"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        meta, body = parse_frontmatter(text)
        title = str(meta.get("title") or path.stem)
        layer, section = layer_and_section(rel)
        pages.append(
            VaultPage(
                rel=rel,
                path=path,
                title=title,
                body=body,
                meta=meta,
                layer=layer,
                section=section,
            )
        )
    return pages


def get_topics(page: VaultPage) -> list[str]:
    topics: list[str] = []
    for key in ("tags", "categories", "topics"):
        val = page.meta.get(key)
        if not val:
            continue
        if isinstance(val, list):
            topics.extend(str(v) for v in val)
        else:
            topics.append(str(val))
    return topics


def get_aliases(page: VaultPage) -> list[str]:
    aliases: list[str] = []
    for key in ("aliases", "aka", "alias"):
        val = page.meta.get(key)
        if not val:
            continue
        if isinstance(val, list):
            aliases.extend(str(v) for v in val)
        else:
            aliases.append(str(val))
    aliases.append(page.stem)
    dated = DATED_STEM_SUFFIX.match(page.stem)
    if dated:
        aliases.append(dated.group(1))
    return [a.strip() for a in aliases if a.strip()]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text)
    return text.strip("-")
