import html
import os
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from config import OUTPUTS_DIR, RAW_DIR, TWIN_PROFILE, WIKI_DIR, WORKSPACE_PATH
from llm_provider import model_name, normalize_provider
from query_engine import generate_query_answer
from query_retrieval import load_index
from save_query_output import save_output

HOST = os.environ.get("QUERY_WEB_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUERY_WEB_PORT", "5050"))
WIKI_ROOT = WIKI_DIR
OUTPUT_ROOT = OUTPUTS_DIR
RAW_ROOT = RAW_DIR

SESSIONS: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Self-Wiki Query", version="0.1.0")


def markdown_to_html(markdown: str, *, base: str = "wiki") -> str:
    """Small markdown renderer for model answers without another dependency."""
    blocks = []
    in_list = False
    in_code = False
    fence_lang = ""
    code_lines = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            blocks.append("</ul>")
            in_list = False

    def close_code_fence() -> None:
        nonlocal in_code, fence_lang, code_lines
        body = html.escape(chr(10).join(code_lines))
        if fence_lang == "mermaid":
            blocks.append(f'<pre class="mermaid">{body}</pre>')
        else:
            blocks.append(f"<pre><code>{body}</code></pre>")
        code_lines = []
        in_code = False
        fence_lang = ""

    for raw_line in markdown.splitlines():
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
            level = min(len(stripped) - len(stripped.lstrip("#")), 3)
            text = stripped[level:].strip()
            blocks.append(f"<h{level}>{format_inline(text, base=base)}</h{level}>")
        elif stripped.startswith(">"):
            close_list()
            blocks.append(
                f"<blockquote>{format_inline(stripped[1:].strip(), base=base)}</blockquote>"
            )
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{format_inline(stripped[2:].strip(), base=base)}</li>")
        else:
            close_list()
            blocks.append(f"<p>{format_inline(stripped, base=base)}</p>")

    close_list()
    if in_code:
        close_code_fence()
    return "\n".join(blocks)


def format_inline(text: str, *, base: str = "wiki") -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"\[\[([^\]]+)\]\]",
        lambda match: render_wikilink(html.unescape(match.group(1)), base=base),
        escaped,
    )
    return escaped


def render_wikilink(raw_target: str, *, base: str = "wiki") -> str:
    target, label = split_wikilink(raw_target)
    href = wikilink_href(target, base=base)
    text = html.escape(label or target)
    if not href:
        return f"<code>[[{text}]]</code>"
    return f'<a href="{html.escape(href, quote=True)}">{text}</a>'


def split_wikilink(raw_target: str) -> tuple[str, str]:
    if "|" in raw_target:
        target, label = raw_target.split("|", 1)
        return target.strip(), label.strip()
    return raw_target.strip(), raw_target.strip()


def wikilink_href(target: str, *, base: str = "wiki") -> str | None:
    clean = target.strip()
    if not clean:
        return None

    if clean.startswith("../raw/"):
        return f"/raw/{quote(clean.removeprefix('../raw/'), safe='/')}"
    if clean.startswith("self-wiki/raw/"):
        return f"/raw/{quote(clean.removeprefix('self-wiki/raw/'), safe='/')}"
    if clean.startswith("../outputs/"):
        return f"/outputs/{quote(clean.removeprefix('../outputs/'), safe='/')}"
    if clean.startswith("self-wiki/outputs/"):
        return f"/outputs/{quote(clean.removeprefix('self-wiki/outputs/'), safe='/')}"
    if clean.startswith("../wiki/"):
        return f"/wiki/{quote(clean.removeprefix('../wiki/'), safe='/')}"
    if clean.startswith("self-wiki/wiki/"):
        return f"/wiki/{quote(clean.removeprefix('self-wiki/wiki/'), safe='/')}"
    if clean.startswith("wiki/"):
        return f"/wiki/{quote(clean.removeprefix('wiki/'), safe='/')}"

    if base == "raw":
        return None
    if base == "outputs" and clean.endswith(".md"):
        return f"/wiki/{quote(clean, safe='/')}"
    return f"/wiki/{quote(clean, safe='/')}"


def page_shell(
    content: str,
    *,
    query: str = "",
    session_id: str = "",
    provider: str = "mlx",
) -> str:
    selected_provider = normalize_provider(provider)
    model = model_name(selected_provider)
    query_value = html.escape(query, quote=True)
    session_input = (
        f'<input type="hidden" name="session_id" value="{html.escape(session_id, quote=True)}">'
        if session_id
        else ""
    )
    provider_options = []
    for option in ("mlx", "gemini", "openai"):
        labels = {
            "mlx": "MLX (local)",
            "gemini": "Gemini (cloud)",
            "openai": "OpenAI (cloud)",
        }
        label = labels[option]
        selected = " selected" if option == selected_provider else ""
        provider_options.append(
            f'<option value="{option}"{selected}>{html.escape(label)}</option>'
        )
    provider_select = "".join(provider_options)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Self-Wiki Query</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --bg-accent-1: rgba(139, 92, 246, 0.12);
      --bg-accent-2: rgba(6, 182, 212, 0.1);
      --bg-gradient-start: #ffffff;
      --bg-gradient-end: #eef2ff;
      --panel: rgba(255, 255, 255, 0.92);
      --panel-strong: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: rgba(15, 23, 42, 0.12);
      --accent: #7c3aed;
      --accent-2: #0891b2;
      --good: #059669;
      --link: #0369a1;
      --heading-2: #6d28d9;
      --body-soft: #334155;
      --question: #5b21b6;
      --input-bg: rgba(255, 255, 255, 0.96);
      --nav-bg: rgba(255, 255, 255, 0.88);
      --blockquote-bg: rgba(8, 145, 178, 0.08);
      --blockquote-text: #0f766e;
      --code-text: #92400e;
      --code-bg: rgba(245, 158, 11, 0.12);
      --pre-bg: #f1f5f9;
      --source-bg: rgba(248, 250, 252, 0.96);
      --list-bg: rgba(255, 255, 255, 0.96);
      --shadow: rgba(15, 23, 42, 0.08);
      --error-border: rgba(220, 38, 38, 0.35);
      --error-bg: rgba(254, 226, 226, 0.72);
      --button-text: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, var(--bg-accent-1), transparent 34rem),
        radial-gradient(circle at top right, var(--bg-accent-2), transparent 32rem),
        linear-gradient(135deg, var(--bg-gradient-start) 0%, var(--bg) 54%, var(--bg-gradient-end) 100%);
    }}
    .wrap {{ width: min(1120px, calc(100vw - 32px)); margin: 0 auto; padding: 48px 0; }}
    .hero {{ display: grid; gap: 22px; margin-bottom: 28px; }}
    .eyebrow {{ color: var(--good); font-size: 13px; letter-spacing: .14em; text-transform: uppercase; }}
    .home-link {{
      color: inherit;
      text-decoration: none;
    }}
    .home-link:hover {{ text-decoration: underline; }}
    .nav {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .nav a {{
      color: var(--text);
      text-decoration: none;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      background: var(--nav-bg);
    }}
    h1 {{ margin: 0; font-size: clamp(36px, 7vw, 74px); line-height: .95; letter-spacing: -0.06em; }}
    .subtitle {{ max-width: 760px; color: var(--muted); font-size: 18px; }}
    .shell {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 20px;
      align-items: start;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: 0 24px 80px var(--shadow);
      backdrop-filter: blur(18px);
    }}
    .query-card {{ padding: 22px; }}
    textarea, .search input {{
      width: 100%;
      min-height: 150px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      color: var(--text);
      background: var(--input-bg);
      outline: none;
      font: inherit;
    }}
    .search input {{ min-height: auto; }}
    textarea:focus, .search input:focus {{ border-color: rgba(139, 92, 246, .8); box-shadow: 0 0 0 4px rgba(139, 92, 246, .15); }}
    .actions {{ display: flex; gap: 12px; align-items: center; margin-top: 14px; flex-wrap: wrap; }}
    button, .button {{
      appearance: none;
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      color: var(--button-text);
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
    }}
    .hint {{ color: var(--muted); font-size: 14px; }}
    .side {{ padding: 22px; position: sticky; top: 20px; }}
    .metric {{ padding: 14px 0; border-top: 1px solid var(--line); }}
    .metric:first-child {{ border-top: 0; padding-top: 0; }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .1em; }}
    .value {{ margin-top: 4px; font-weight: 700; overflow-wrap: anywhere; }}
    .answer {{ padding: 26px; margin-top: 20px; }}
    .answer h1, .answer h2, .answer h3 {{ letter-spacing: -0.03em; line-height: 1.1; color: var(--text); }}
    .answer h1 {{ font-size: 32px; }}
    .answer h2 {{ margin-top: 28px; color: var(--heading-2); }}
    .answer p, .answer li {{ color: var(--body-soft); }}
    a {{ color: var(--link); }}
    blockquote {{ margin: 18px 0; padding: 16px 18px; border-left: 4px solid var(--accent-2); background: var(--blockquote-bg); border-radius: 16px; color: var(--blockquote-text); }}
    code {{ color: var(--code-text); background: var(--code-bg); padding: 2px 6px; border-radius: 7px; }}
    pre {{ overflow: auto; padding: 16px; border-radius: 16px; background: var(--pre-bg); }}
    pre.mermaid {{
      overflow-x: auto;
      margin: 1rem 0;
      padding: 0;
      background: transparent;
      border: 0;
    }}
    pre.mermaid svg {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
    .sources {{ display: grid; gap: 10px; margin-top: 18px; }}
    .source {{ padding: 12px 14px; border: 1px solid var(--line); border-radius: 16px; background: var(--source-bg); }}
    .source small {{ color: var(--muted); }}
    .list {{ display: grid; gap: 12px; }}
    .list-item {{ display: block; padding: 14px 16px; border: 1px solid var(--line); border-radius: 18px; background: var(--list-bg); color: var(--text); text-decoration: none; }}
    .list-item small {{ display: block; color: var(--muted); margin-top: 3px; overflow-wrap: anywhere; }}
    .search {{ display: flex; gap: 10px; margin-bottom: 16px; }}
    .provider-row {{ display: flex; gap: 12px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }}
    .provider-row label {{ color: var(--muted); font-size: 14px; }}
    .provider-select {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 10px 14px;
      background: var(--input-bg);
      color: var(--text);
      font: inherit;
    }}
    .turn {{ padding: 22px; margin-top: 16px; }}
    .question {{ color: var(--question); font-weight: 700; }}
    .error {{ border-color: var(--error-border); background: var(--error-bg); }}
    @media (max-width: 860px) {{ .shell {{ grid-template-columns: 1fr; }} .side {{ position: static; }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <a href="/" class="eyebrow home-link">Socratic Mirror</a>
      <h1>Self-Wiki</h1>
      <p class="subtitle">Ask questions via the same pipeline as <code>make query</code>. Citations in answers link to wiki and raw sources.</p>
      <nav class="nav">
        <a href="/wiki">Wiki</a>
        <a href="/outputs">Outputs</a>
        <a href="/profile">Profile</a>
        <a href="/sessions">Sessions</a>
      </nav>
    </section>
    <section class="shell">
      <div>
        <form class="card query-card" method="post" action="/query">
          {session_input}
          <div class="provider-row">
            <label for="provider">Provider</label>
            <select id="provider" name="provider" class="provider-select">{provider_select}</select>
          </div>
          <textarea name="question" placeholder="Ask about values, personality logic, strengths, blind spots..." autofocus>{query_value}</textarea>
          <div class="actions">
            <button type="submit">{'Ask Follow-up' if session_id else 'Ask Wiki'}</button>
            <span class="hint">Local server: {html.escape(HOST)}:{PORT}</span>
          </div>
        </form>
        {content}
      </div>
      <aside class="card side">
        <div class="metric"><div class="label">Provider</div><div class="value">{html.escape(selected_provider)}</div></div>
        <div class="metric"><div class="label">Model</div><div class="value">{html.escape(model)}</div></div>
        <div class="metric"><div class="label">Privacy</div><div class="value">Listening on {html.escape(HOST)}:{PORT}</div></div>
        <div class="metric"><div class="label">Loop</div><div class="value">{'Session ' + html.escape(session_id[:8]) if session_id else 'New session on first query'}</div></div>
        <div class="metric"><div class="label">CLI Equivalent</div><div class="value"><code>make query Q="..."</code></div></div>
      </aside>
    </section>
  </main>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{ startOnLoad: false, securityLevel: "strict", theme: "default" }});
    document.addEventListener("DOMContentLoaded", () => {{
      const nodes = document.querySelectorAll("pre.mermaid");
      if (nodes.length) {{
        mermaid.run({{ nodes }});
      }}
    }});
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    wiki_count = len(wiki_items())
    output_count = len(list(OUTPUT_ROOT.glob("*.md")))
    intro = f"""<section class="card answer">
      <h2>Query</h2>
      <p>Ask a question, inspect retrieved wiki/raw evidence, then follow up in the same session.</p>
      <p class="hint">{wiki_count} wiki page(s) · {output_count} saved output(s)</p>
    </section>"""
    return HTMLResponse(page_shell(intro))


@app.post("/query", response_class=HTMLResponse)
def query_page(
    question: str = Form(...),
    session_id: str = Form(""),
    provider: str = Form("mlx"),
) -> HTMLResponse:
    clean_question = question.strip()
    llm_provider = normalize_provider(provider)
    if not clean_question:
        return HTMLResponse(
            page_shell(
                '<section class="card answer error">Please enter a question.</section>',
                query=question,
                session_id=session_id,
                provider=llm_provider,
            ),
            status_code=400,
        )

    session = get_or_create_session(session_id, clean_question, provider=llm_provider)
    try:
        result = generate_query_answer(
            clean_question,
            index=load_index(required=False),
            messages=session["messages"],
            provider=session["provider"],
        )
        output_path = save_output(session["title"], result["messages"])
    except Exception as exc:
        body = f'<section class="card answer error"><h2>Query failed</h2><p>{html.escape(str(exc))}</p></section>'
        return HTMLResponse(
            page_shell(
                body,
                query=clean_question,
                session_id=session["id"],
                provider=session["provider"],
            ),
            status_code=500,
        )

    session["turns"].append(
        {
            "question": clean_question,
            "answer": result["answer"],
            "profile": result["profile"],
            "language": result["language"],
            "provider": result["provider"],
            "model": result.get("model", ""),
            "candidates": result["candidates"],
            "output_path": str(output_path),
            "pending_path": result.get("pending_path", ""),
        }
    )
    session["output_path"] = str(output_path)
    return RedirectResponse(f"/sessions/{session['id']}", status_code=303)


@app.get("/sessions", response_class=HTMLResponse)
def sessions_page() -> HTMLResponse:
    items = []
    for session in reversed(list(SESSIONS.values())):
        title = html.escape(session["title"])
        items.append(
            f"""<a class="list-item" href="/sessions/{html.escape(session['id'])}">
              {title}<small>{len(session['turns'])} turn(s)</small>
            </a>"""
        )
    body = f"""<section class="card answer">
      <h2>Sessions</h2>
      <div class="list">{''.join(items) or '<p>No sessions yet.</p>'}</div>
    </section>"""
    return HTMLResponse(page_shell(body))


@app.get("/sessions/{session_id}", response_class=HTMLResponse)
def session_page(session_id: str) -> HTMLResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    body = render_session(session)
    return HTMLResponse(
        page_shell(body, session_id=session_id, provider=session.get("provider", "mlx"))
    )


@app.post("/api/query")
def query_api(payload: dict) -> JSONResponse:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    session = get_or_create_session(
        str(payload.get("session_id", "")),
        question,
        provider=str(payload.get("provider", "mlx")),
    )
    result = generate_query_answer(
        question,
        index=load_index(required=False),
        messages=session["messages"],
        provider=session["provider"],
    )
    output_path = save_output(session["title"], result["messages"])
    session["turns"].append(
        {
            "question": question,
            "answer": result["answer"],
            "profile": result["profile"],
            "language": result["language"],
            "provider": result["provider"],
            "model": result.get("model", ""),
            "candidates": result["candidates"],
            "output_path": str(output_path),
            "pending_path": result.get("pending_path", ""),
        }
    )
    session["output_path"] = str(output_path)
    result.pop("messages", None)
    result["output_path"] = str(output_path)
    result["session_id"] = session["id"]
    return JSONResponse(result)


@app.get("/wiki", response_class=HTMLResponse)
def wiki_index(q: str = "") -> HTMLResponse:
    query = q.strip().lower()
    items = []
    for item in wiki_items():
        haystack = " ".join(
            [
                item["name"],
                item["path"],
                " ".join(item.get("tags", [])),
            ]
        ).lower()
        if query and query not in haystack:
            continue
        href = "/wiki/" + quote(item["wiki_path"], safe="/")
        tags = ", ".join(item.get("tags", [])[:5])
        items.append(
            f"""<a class="list-item" href="{href}">
              {html.escape(item['name'])}
              <small>{html.escape(item['path'])}{' · ' + html.escape(tags) if tags else ''}</small>
            </a>"""
        )
    body = f"""<section class="card answer">
      <h2>Wiki</h2>
      {search_form('/wiki', q)}
      <div class="list">{''.join(items[:300]) or '<p>No wiki pages found.</p>'}</div>
    </section>"""
    return HTMLResponse(page_shell(body))


@app.get("/wiki/{note_path:path}", response_class=HTMLResponse)
def wiki_page(note_path: str) -> HTMLResponse:
    path = resolve_markdown_path(WIKI_ROOT, note_path)
    text = read_private_file(path)
    title = html.escape(path.stem)
    body = f"""<section class="card answer">
      <div class="eyebrow">Wiki Note</div>
      <h2>{title}</h2>
      {markdown_to_html(strip_frontmatter(text), base='wiki')}
    </section>"""
    return HTMLResponse(page_shell(body))


@app.get("/outputs", response_class=HTMLResponse)
def outputs_index(q: str = "") -> HTMLResponse:
    query = q.strip().lower()
    files = sorted(
        [p for p in OUTPUT_ROOT.glob("*.md") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    items = []
    for path in files:
        if query and query not in path.name.lower():
            continue
        href = "/outputs/" + quote(path.name, safe="/")
        items.append(
            f"""<a class="list-item" href="{href}">
              {html.escape(path.stem)}
              <small>{html.escape(path.name)}</small>
            </a>"""
        )
    body = f"""<section class="card answer">
      <h2>Generated Outputs</h2>
      {search_form('/outputs', q)}
      <div class="list">{''.join(items[:200]) or '<p>No outputs found.</p>'}</div>
    </section>"""
    return HTMLResponse(page_shell(body))


@app.get("/outputs/{output_path:path}", response_class=HTMLResponse)
def output_page(output_path: str) -> HTMLResponse:
    path = resolve_markdown_path(OUTPUT_ROOT, output_path)
    text = read_private_file(path)
    body = f"""<section class="card answer">
      <div class="eyebrow">Generated Output</div>
      <h2>{html.escape(path.stem)}</h2>
      {markdown_to_html(strip_frontmatter(text), base='outputs')}
    </section>"""
    return HTMLResponse(page_shell(body))


@app.get("/profile", response_class=HTMLResponse)
def profile_page() -> HTMLResponse:
    if not TWIN_PROFILE.exists():
        body = """<section class="card answer">
      <h2>Digital Twin Profile</h2>
      <p><code>twin/PROFILE.md</code> is not generated yet. It will appear after Iter 3 (<code>build_twin_profile</code> in post-ingest).</p>
    </section>"""
        return HTMLResponse(page_shell(body))

    text = read_private_file(TWIN_PROFILE)
    body = f"""<section class="card answer">
      <div class="eyebrow">Digital Twin</div>
      <h2>Profile</h2>
      {markdown_to_html(strip_frontmatter(text), base='wiki')}
    </section>"""
    return HTMLResponse(page_shell(body))


@app.get("/raw/{raw_path:path}", response_class=HTMLResponse)
def raw_page(raw_path: str) -> HTMLResponse:
    path = resolve_markdown_path(RAW_ROOT, raw_path)
    text = read_private_file(path)
    body = f"""<section class="card answer">
      <div class="eyebrow">Private Raw Source</div>
      <h2>{html.escape(path.name)}</h2>
      {markdown_to_html(strip_frontmatter(text), base='raw')}
    </section>"""
    return HTMLResponse(page_shell(body))


def get_or_create_session(
    session_id: str, title: str, *, provider: str = "mlx"
) -> dict[str, Any]:
    if session_id and session_id in SESSIONS:
        session = SESSIONS[session_id]
        session["provider"] = normalize_provider(provider)
        return session

    new_id = uuid.uuid4().hex
    session = {
        "id": new_id,
        "title": title,
        "provider": normalize_provider(provider),
        "messages": [],
        "turns": [],
        "output_path": "",
    }
    SESSIONS[new_id] = session
    return session


def render_session(session: dict[str, Any]) -> str:
    turns = []
    for idx, turn in enumerate(session["turns"], start=1):
        candidate_cards = render_candidate_cards(turn.get("candidates", []))
        output_name = Path(turn.get("output_path", "")).name
        output_link = (
            f'<a href="/outputs/{quote(output_name, safe="/")}">self-wiki/outputs/{html.escape(output_name)}</a>'
            if output_name
            else "not saved"
        )
        turns.append(
            f"""<section class="card turn">
              <div class="eyebrow">Turn {idx} · {html.escape(turn['profile'])} · {html.escape(turn['language'])} · {html.escape(str(turn.get('provider', 'mlx')))}</div>
              <p class="question">{html.escape(turn['question'])}</p>
              {markdown_to_html(turn['answer'], base='outputs')}
              <h2>Retrieved Evidence</h2>
              <div class="sources">{candidate_cards}</div>
              <p class="hint">Saved to {output_link}</p>
            </section>"""
        )

    return f"""<section class="card answer">
      <div class="eyebrow">Conversation Loop</div>
      <h2>{html.escape(session['title'])}</h2>
      <p>Use the query box above to ask a follow-up in this same session.</p>
    </section>
    {''.join(turns)}"""


def render_candidate_cards(candidates: list[dict[str, Any]]) -> str:
    cards = []
    for item in candidates[:10]:
        path = str(item.get("path", ""))
        href = wikilink_href(path, base="outputs") or "#"
        cards.append(
            f"""<div class="source">
              <strong><a href="{html.escape(href, quote=True)}">{html.escape(str(item.get('name', path)))}</a></strong>
              <small>score {html.escape(str(item.get('score', '')))} · {html.escape(path)}</small>
            </div>"""
        )
    return "".join(cards) or '<div class="source">No candidates retrieved.</div>'


def wiki_items() -> list[dict[str, Any]]:
    index = load_index(required=False)
    items = []
    seen: set[str] = set()
    for name, data in index.get("topics", {}).items():
        rel_path = str(data.get("path", ""))
        if not rel_path:
            continue
        path = WORKSPACE_PATH / rel_path
        if not path.exists() or path.suffix.lower() != ".md":
            continue
        wiki_path = str(path.relative_to(WIKI_ROOT))
        seen.add(str(path.resolve()))
        items.append(
            {
                "name": str(name),
                "path": rel_path,
                "wiki_path": wiki_path,
                "tags": [str(t) for t in data.get("tags", [])],
            }
        )

    for path in WIKI_ROOT.rglob("*.md"):
        if str(path.resolve()) in seen:
            continue
        items.append(
            {
                "name": path.stem,
                "path": str(path.relative_to(WORKSPACE_PATH)),
                "wiki_path": str(path.relative_to(WIKI_ROOT)),
                "tags": [],
            }
        )

    return sorted(items, key=lambda item: item["name"].lower())


def search_form(action: str, value: str) -> str:
    return f"""<form class="search" method="get" action="{html.escape(action, quote=True)}">
      <input name="q" value="{html.escape(value, quote=True)}" placeholder="Search">
      <button type="submit">Search</button>
    </form>"""


def normalize_requested_path(requested_path: str) -> str:
    clean = unquote(requested_path).strip().replace("\\", "/").lstrip("/")
    prefixes = (
        "../raw/",
        "self-wiki/raw/",
        "../wiki/",
        "self-wiki/wiki/",
        "../outputs/",
        "self-wiki/outputs/",
        "wiki/",
        "raw/",
    )
    for prefix in prefixes:
        if clean.startswith(prefix):
            clean = clean.removeprefix(prefix)
            break
    parts = [part for part in Path(clean).parts if part not in ("", ".")]
    if ".." in parts:
        raise HTTPException(status_code=400, detail="Invalid path")
    return str(Path(*parts)) if parts else ""


def resolve_markdown_path(root: Path, requested_path: str) -> Path:
    clean = normalize_requested_path(requested_path)
    if not clean:
        raise HTTPException(status_code=404, detail="File not found")

    root_resolved = root.resolve()
    candidate = (root / clean).absolute()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc

    resolved = candidate.resolve()
    if resolved.is_dir():
        raise HTTPException(status_code=404, detail="File not found")
    if not resolved.exists() and resolved.suffix.lower() != ".md":
        resolved = resolved.with_suffix(".md")
    if not resolved.exists() or resolved.suffix.lower() != ".md":
        raise HTTPException(status_code=404, detail="File not found")
    return resolved


def read_private_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        _, sep, rest = text[4:].partition("\n---")
        if sep:
            return rest.lstrip("\n")
    return text


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("query_server:app", host=HOST, port=PORT, reload=False)
