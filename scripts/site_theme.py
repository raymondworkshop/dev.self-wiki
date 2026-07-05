"""Shared static-site theme aligned with query-web (query_server.py)."""

from __future__ import annotations

import html

SITE_CSS = """
    :root {
      color-scheme: light;
      --bg: #f8fafc;
      --bg-accent-1: rgba(139, 92, 246, 0.12);
      --bg-accent-2: rgba(6, 182, 212, 0.1);
      --bg-gradient-start: #ffffff;
      --bg-gradient-end: #eef2ff;
      --panel: rgba(255, 255, 255, 0.92);
      --text: #0f172a;
      --muted: #64748b;
      --line: rgba(15, 23, 42, 0.12);
      --accent: #7c3aed;
      --accent-2: #0891b2;
      --good: #059669;
      --link: #0369a1;
      --heading-2: #6d28d9;
      --body-soft: #334155;
      --nav-bg: rgba(255, 255, 255, 0.88);
      --blockquote-bg: rgba(8, 145, 178, 0.08);
      --blockquote-text: #0f766e;
      --code-text: #92400e;
      --code-bg: rgba(245, 158, 11, 0.12);
      --pre-bg: #f1f5f9;
      --list-bg: rgba(255, 255, 255, 0.96);
      --shadow: rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, var(--bg-accent-1), transparent 34rem),
        radial-gradient(circle at top right, var(--bg-accent-2), transparent 32rem),
        linear-gradient(135deg, var(--bg-gradient-start) 0%, var(--bg) 54%, var(--bg-gradient-end) 100%);
    }
    .wrap { width: min(1120px, calc(100vw - 32px)); margin: 0 auto; padding: 48px 0 72px; }
    .hero { display: grid; gap: 18px; margin-bottom: 24px; }
    .hero-compact { gap: 14px; margin-bottom: 20px; }
    .hero-compact h1 { font-size: clamp(28px, 5vw, 42px); }
    .eyebrow { color: var(--good); font-size: 13px; letter-spacing: .14em; text-transform: uppercase; }
    .home-link { color: inherit; text-decoration: none; }
    .home-link:hover { text-decoration: underline; }
    .nav { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
    .nav a {
      color: var(--text);
      text-decoration: none;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      background: var(--nav-bg);
    }
    .nav a.active {
      border-color: rgba(139, 92, 246, 0.45);
      background: rgba(139, 92, 246, 0.1);
      font-weight: 600;
    }
    h1 { margin: 0; font-size: clamp(36px, 7vw, 56px); line-height: .95; letter-spacing: -0.06em; }
    .subtitle { max-width: 760px; color: var(--muted); font-size: 18px; margin: 0; }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: 0 24px 80px var(--shadow);
      backdrop-filter: blur(18px);
    }
    .answer { padding: 26px; }
    .answer h1, .answer h2, .answer h3, .answer h4 {
      letter-spacing: -0.03em;
      line-height: 1.15;
      color: var(--text);
    }
    .answer h1 { font-size: 32px; margin-top: 0; }
    .answer h2 { margin-top: 28px; color: var(--heading-2); font-size: 24px; }
    .answer h3 { font-size: 20px; margin-top: 22px; }
    .answer p, .answer li { color: var(--body-soft); }
    .answer ul { padding-left: 1.25rem; }
    .answer table {
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0;
      font-size: 15px;
    }
    .answer th, .answer td {
      border: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
    }
    .answer th { background: rgba(238, 242, 255, 0.8); }
    a { color: var(--link); }
    blockquote {
      margin: 18px 0;
      padding: 16px 18px;
      border-left: 4px solid var(--accent-2);
      background: var(--blockquote-bg);
      border-radius: 16px;
      color: var(--blockquote-text);
    }
    code { color: var(--code-text); background: var(--code-bg); padding: 2px 6px; border-radius: 7px; }
    pre {
      overflow: auto;
      padding: 16px;
      border-radius: 16px;
      background: var(--pre-bg);
    }
    pre code { background: transparent; padding: 0; color: inherit; }
    pre.mermaid {
      overflow-x: auto;
      margin: 1rem 0;
      padding: 0;
      background: transparent;
      border: 0;
    }
    pre.mermaid svg { max-width: 100%; height: auto; display: block; margin: 0 auto; }
    .path {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      overflow-wrap: anywhere;
    }
    .list { display: grid; gap: 12px; }
    .list-item {
      display: block;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--list-bg);
      color: var(--text);
      text-decoration: none;
    }
    .list-item:hover { border-color: rgba(139, 92, 246, 0.35); }
    .list-item small {
      display: block;
      color: var(--muted);
      margin-top: 3px;
      overflow-wrap: anywhere;
    }
    @media (max-width: 860px) {
      .wrap { padding-top: 28px; }
    }
"""

NAV_ITEMS = (
    ("home", "Home", "/index.html"),
    ("raw", "Raw", "/raw/index.html"),
    ("compression", "Compression", "/compression/index.html"),
    ("wiki", "Wiki", "/wiki/index.html"),
    ("discovery", "Discovery", "/discovery/index.html"),
    ("gap", "Gap", "/gap/index.html"),
    ("evolution", "Evolution", "/evolution/index.html"),
    ("twin", "Twin", "/twin/PROFILE.html"),
    ("outputs", "Output", "/outputs/index.html"),
)


def eyebrow_for_path(rel_path: str) -> str:
    if rel_path in ("INDEX.md", "index.html"):
        return "Home"
    prefix = rel_path.split("/", 1)[0]
    labels = {
        "wiki": "Wiki Note",
        "raw": "Raw Source",
        "compression": "Compression Digest",
        "twin": "Digital Twin",
        "outputs": "Query Output",
        "discovery": "Discovery Report",
        "gap": "Gap Report",
        "evolution": "Evolution Report",
        "log": "Pipeline Log",
    }
    return labels.get(prefix, "Self-Wiki")


def nav_active_for_path(rel_path: str) -> str:
    if rel_path in ("INDEX.md", "index.html"):
        return "home"
    return rel_path.split("/", 1)[0]


def render_nav(active: str) -> str:
    parts = []
    for key, label, href in NAV_ITEMS:
        if key == active:
            parts.append(f'<a href="{href}" class="active">{html.escape(label)}</a>')
        else:
            parts.append(f'<a href="{href}">{html.escape(label)}</a>')
    return "".join(parts)


def render_page(
    title: str,
    body_html: str,
    *,
    rel_path: str = "",
    hero_title: str | None = None,
    subtitle: str = "",
    compact: bool = False,
) -> str:
    safe_title = html.escape(title)
    active = nav_active_for_path(rel_path)
    nav = render_nav(active)
    eyebrow = html.escape(eyebrow_for_path(rel_path))
    hero_cls = "hero hero-compact" if compact else "hero"
    display_title = html.escape(hero_title or title)
    subtitle_block = (
        f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle and not compact else ""
    )
    path_block = (
        f'<div class="path">{html.escape(rel_path)}</div>' if rel_path and compact else ""
    )

    if compact:
        header = f"""
    <section class="{hero_cls}">
      <a href="/index.html" class="eyebrow home-link">Socratic Mirror</a>
      <nav class="nav">{nav}</nav>
    </section>"""
        content_block = f"""
    <section class="card answer">
      <div class="eyebrow">{eyebrow}</div>
      {path_block}
      {body_html}
    </section>"""
    else:
        header = f"""
    <section class="{hero_cls}">
      <a href="/index.html" class="eyebrow home-link">Socratic Mirror</a>
      <h1>{display_title}</h1>
      {subtitle_block}
      <nav class="nav">{nav}</nav>
    </section>"""
        content_block = f"""
    <section class="card answer">
      {body_html}
    </section>"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} · Self-Wiki</title>
  <style>{SITE_CSS}</style>
</head>
<body>
  <main class="wrap">{header}{content_block}
  </main>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <script>mermaid.initialize({{ startOnLoad: true, securityLevel: "strict" }});</script>
</body>
</html>"""
