import html
import os
import re
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from llm_provider import model_name, provider_name
from query_wiki import generate_query_answer, load_index, save_output

HOST = os.environ.get("QUERY_WEB_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUERY_WEB_PORT", "5050"))

app = FastAPI(title="Self-Wiki Query", version="0.1.0")


def markdown_to_html(markdown: str) -> str:
    """Small markdown renderer for model answers without another dependency."""
    blocks = []
    in_list = False
    in_code = False
    code_lines = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            blocks.append("</ul>")
            in_list = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                blocks.append(
                    f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>"
                )
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
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
            blocks.append(f"<h{level}>{format_inline(text)}</h{level}>")
        elif stripped.startswith(">"):
            close_list()
            blocks.append(f"<blockquote>{format_inline(stripped[1:].strip())}</blockquote>")
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{format_inline(stripped[2:].strip())}</li>")
        else:
            close_list()
            blocks.append(f"<p>{format_inline(stripped)}</p>")

    close_list()
    if in_code:
        blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(blocks)


def format_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[\[([^\]]+)\]\]", r"<code>[[\1]]</code>", escaped)
    return escaped


def page_shell(content: str, *, query: str = "") -> str:
    provider = provider_name()
    model = model_name(provider)
    query_value = html.escape(query, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Self-Wiki Query</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0b1020;
      --panel: rgba(17, 24, 39, 0.76);
      --panel-strong: rgba(31, 41, 55, 0.92);
      --text: #eef2ff;
      --muted: #9ca3af;
      --line: rgba(148, 163, 184, 0.22);
      --accent: #8b5cf6;
      --accent-2: #06b6d4;
      --good: #34d399;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(139, 92, 246, 0.34), transparent 34rem),
        radial-gradient(circle at top right, rgba(6, 182, 212, 0.22), transparent 32rem),
        linear-gradient(135deg, #080b14 0%, var(--bg) 54%, #111827 100%);
    }}
    .wrap {{ width: min(1120px, calc(100vw - 32px)); margin: 0 auto; padding: 48px 0; }}
    .hero {{ display: grid; gap: 22px; margin-bottom: 28px; }}
    .eyebrow {{ color: var(--good); font-size: 13px; letter-spacing: .14em; text-transform: uppercase; }}
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
      box-shadow: 0 24px 80px rgba(0, 0, 0, .35);
      backdrop-filter: blur(18px);
    }}
    .query-card {{ padding: 22px; }}
    textarea {{
      width: 100%;
      min-height: 150px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      color: var(--text);
      background: rgba(2, 6, 23, .62);
      outline: none;
      font: inherit;
    }}
    textarea:focus {{ border-color: rgba(139, 92, 246, .8); box-shadow: 0 0 0 4px rgba(139, 92, 246, .15); }}
    .actions {{ display: flex; gap: 12px; align-items: center; margin-top: 14px; flex-wrap: wrap; }}
    button, .button {{
      appearance: none;
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      color: white;
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
    .answer h1, .answer h2, .answer h3 {{ letter-spacing: -0.03em; line-height: 1.1; }}
    .answer h1 {{ font-size: 32px; }}
    .answer h2 {{ margin-top: 28px; color: #c4b5fd; }}
    .answer p, .answer li {{ color: #dbeafe; }}
    blockquote {{ margin: 18px 0; padding: 16px 18px; border-left: 4px solid var(--accent-2); background: rgba(6, 182, 212, .08); border-radius: 16px; color: #cffafe; }}
    code {{ color: #fef3c7; background: rgba(250, 204, 21, .08); padding: 2px 6px; border-radius: 7px; }}
    pre {{ overflow: auto; padding: 16px; border-radius: 16px; background: rgba(2, 6, 23, .78); }}
    .sources {{ display: grid; gap: 10px; margin-top: 18px; }}
    .source {{ padding: 12px 14px; border: 1px solid var(--line); border-radius: 16px; background: rgba(15, 23, 42, .7); }}
    .source small {{ color: var(--muted); }}
    .error {{ border-color: rgba(248, 113, 113, .45); background: rgba(127, 29, 29, .28); }}
    @media (max-width: 860px) {{ .shell {{ grid-template-columns: 1fr; }} .side {{ position: static; }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="eyebrow">Socratic Mirror</div>
      <h1>Ask your self-wiki</h1>
      <p class="subtitle">A private query surface over your curated wiki memory. Choose MLX for fully local reasoning, or Gemini for deeper synthesis over selected wiki evidence.</p>
    </section>
    <section class="shell">
      <div>
        <form class="card query-card" method="post" action="/query">
          <textarea name="question" placeholder="Ask about values, personality logic, strengths, blind spots..." autofocus>{query_value}</textarea>
          <div class="actions">
            <button type="submit">Ask Wiki</button>
            <span class="hint">Local server: {html.escape(HOST)}:{PORT}</span>
          </div>
        </form>
        {content}
      </div>
      <aside class="card side">
        <div class="metric"><div class="label">Provider</div><div class="value">{html.escape(provider)}</div></div>
        <div class="metric"><div class="label">Model</div><div class="value">{html.escape(model)}</div></div>
        <div class="metric"><div class="label">Privacy</div><div class="value">Binds to 127.0.0.1 by default</div></div>
        <div class="metric"><div class="label">CLI Equivalent</div><div class="value"><code>make query</code></div></div>
      </aside>
    </section>
  </main>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(page_shell(""))


@app.post("/query", response_class=HTMLResponse)
def query_page(question: str = Form(...)) -> HTMLResponse:
    clean_question = question.strip()
    if not clean_question:
        return HTMLResponse(
            page_shell(
                '<section class="card answer error">Please enter a question.</section>',
                query=question,
            ),
            status_code=400,
        )

    try:
        result = generate_query_answer(clean_question, index=load_index(required=False))
        output_path = save_output(clean_question, result["messages"])
    except Exception as exc:
        body = f'<section class="card answer error"><h2>Query failed</h2><p>{html.escape(str(exc))}</p></section>'
        return HTMLResponse(page_shell(body, query=clean_question), status_code=500)

    candidate_cards = "\n".join(
        f"""<div class="source">
          <strong>{html.escape(item["name"])}</strong>
          <small>score {item["score"]} · {html.escape(item["path"])}</small>
        </div>"""
        for item in result["candidates"][:8]
    )
    answer_html = markdown_to_html(result["answer"])
    rel_output = Path(output_path).name
    body = f"""<section class="card answer">
      <div class="eyebrow">{html.escape(result["profile"])} · {html.escape(result["language"])}</div>
      {answer_html}
      <h2>Retrieved Evidence</h2>
      <div class="sources">{candidate_cards or '<div class="source">No candidates retrieved.</div>'}</div>
      <p class="hint">Saved to <code>self-wiki/outputs/{html.escape(rel_output)}</code></p>
    </section>"""
    return HTMLResponse(page_shell(body, query=clean_question))


@app.post("/api/query")
def query_api(payload: dict) -> JSONResponse:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    result = generate_query_answer(question, index=load_index(required=False))
    output_path = save_output(question, result["messages"])
    result.pop("messages", None)
    result["output_path"] = str(output_path)
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("query_server:app", host=HOST, port=PORT, reload=False)
