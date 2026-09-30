"""Thin trace HTTP service: GET / UI, POST /ask, GET /source, GET /health (stdlib only)."""

from __future__ import annotations

import argparse
import html
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config import RAW_DIR, WORKSPACE_PATH
from trace_engine import run_trace
from trace_index import ensure_index, get_paragraph

logger = logging.getLogger(__name__)

_CTX_LINES = 12


def _html_page(title: str, body: str, *, extra_head: str = "") -> bytes:
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: light; --ink:#18181b; --muted:#71717a; --line:#e4e4e7; --bg:#fafafa; --card:#fff; --accent:#1d4ed8; --hi:#fef3c7; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif; max-width: 54rem; margin: 0 auto; padding: 2rem 1.25rem 3rem; line-height: 1.6; color: var(--ink); background: var(--bg); }}
h1 {{ font-size: 1.65rem; margin: 0 0 0.25rem; letter-spacing: -0.02em; }}
.meta {{ color: var(--muted); font-size: 0.92rem; margin-bottom: 1.5rem; font-family: ui-sans-serif, system-ui, sans-serif; }}
label {{ display: block; font-weight: 600; margin-bottom: 0.4rem; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.92rem; }}
textarea {{ width: 100%; min-height: 6.5rem; padding: 0.85rem 1rem; border: 1px solid var(--line); border-radius: 10px; font: inherit; background: var(--card); resize: vertical; }}
.row {{ display: flex; gap: 0.75rem; align-items: center; margin-top: 0.85rem; flex-wrap: wrap; font-family: ui-sans-serif, system-ui, sans-serif; }}
button {{ background: var(--ink); color: #fff; border: 0; border-radius: 999px; padding: 0.65rem 1.25rem; font: inherit; font-size: 0.95rem; cursor: pointer; }}
button:disabled {{ opacity: 0.55; cursor: wait; }}
#status {{ color: var(--muted); font-size: 0.9rem; }}
#status.err {{ color: #b91c1c; }}
a {{ color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }}
a:hover {{ text-decoration-thickness: 2px; }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 1.15rem 1.25rem; margin-top: 1.35rem; box-shadow: 0 1px 0 rgba(0,0,0,.03); }}
.card h2 {{ font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin: 0 0 0.85rem; font-weight: 700; }}
#answer.prose {{ white-space: normal; }}
#answer.prose h1, #answer.prose h2, #answer.prose h3 {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 1.1rem 0 0.45rem; line-height: 1.3; }}
#answer.prose h1 {{ font-size: 1.25rem; }}
#answer.prose h2 {{ font-size: 1.05rem; text-transform: none; letter-spacing: 0; color: var(--ink); }}
#answer.prose p {{ margin: 0.55rem 0; }}
#answer.prose ul {{ margin: 0.4rem 0 0.7rem; padding-left: 1.2rem; }}
#answer.prose li {{ margin: 0.3rem 0; }}
#answer.prose blockquote {{ margin: 0.75rem 0; padding: 0.65rem 0.9rem; border-left: 3px solid #a1a1aa; background: #f4f4f5; border-radius: 0 8px 8px 0; color: #3f3f46; white-space: pre-wrap; }}
#answer.prose .cite, #answer.prose .wikilink {{ font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.88em; background: #eff6ff; padding: 0.1rem 0.35rem; border-radius: 4px; text-decoration: none; }}
#answer.prose .cite:hover, #answer.prose .wikilink:hover {{ background: #dbeafe; }}
#answer.prose strong {{ font-weight: 700; }}
#sources a {{ display: block; margin: 0.35rem 0; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.9rem; }}
.code-view {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.82rem; line-height: 1.45; border: 1px solid var(--line); border-radius: 10px; overflow: auto; background: #fff; max-height: 75vh; }}
.code-view .line {{ display: grid; grid-template-columns: 3.5rem 1fr; gap: 0.75rem; padding: 0 0.75rem; }}
.code-view .line:hover {{ background: #f4f4f5; }}
.code-view .ln {{ color: var(--muted); text-align: right; user-select: none; padding: 0.15rem 0; }}
.code-view .tx {{ white-space: pre-wrap; word-break: break-word; padding: 0.15rem 0; }}
.code-view .line.hi {{ background: var(--hi); }}
.code-view .line.hi .ln {{ color: #92400e; font-weight: 700; }}
.nav {{ font-family: ui-sans-serif, system-ui, sans-serif; margin-top: 1.25rem; }}
</style>
{extra_head}
</head>
<body>
{body}
</body>
</html>
"""
    return doc.encode("utf-8")


def _home_page(*, paragraph_count: int | None, built_at: str | None) -> bytes:
    meta = f"{paragraph_count or 0} paragraphs"
    if built_at:
        meta += f" · index {html.escape(str(built_at))}"
    body = f"""
<h1>trace</h1>
<p class="meta">Raw-only Q&amp;A with verbatim cites · {meta} · <a href="/health">health</a></p>
<label for="q">Question</label>
<textarea id="q" placeholder="what are my core values?"></textarea>
<div class="row">
  <button id="ask" type="button">Ask</button>
  <span id="status"></span>
</div>
<div id="answerCard" class="card" hidden>
  <h2>Answer</h2>
  <div id="answer" class="prose"></div>
</div>
<div id="sourcesCard" class="card" hidden>
  <h2>Retrieval candidates</h2>
  <div id="sources"></div>
</div>
<script>
const qEl = document.getElementById('q');
const askBtn = document.getElementById('ask');
const statusEl = document.getElementById('status');
const answerEl = document.getElementById('answer');
const answerCard = document.getElementById('answerCard');
const sourcesEl = document.getElementById('sources');
const sourcesCard = document.getElementById('sourcesCard');

function escapeHtml(s) {{
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}}

function sourceHref(path, pTag, start, end) {{
  const id = pTag ? (path + pTag) : path;
  let href = '/source?id=' + encodeURIComponent(id);
  if (start) href += '&start=' + start;
  if (end) href += '&end=' + end;
  if (start) href += '#L' + start;
  return href;
}}

function linkifyCites(escaped) {{
  // [[raw/...]] · #p12 · L84–L91  (en/em dash or hyphen)
  let s = escaped.replace(
    /\\[\\[(raw\\/[^\\]]+)\\]\\]\\s*·\\s*(#p\\d+)\\s*·\\s*L(\\d+)\\s*[–—-]\\s*L?(\\d+)/g,
    (_, path, pTag, a, b) => {{
      const href = sourceHref(path, pTag, a, b);
      const label = '[[' + path + ']] · ' + pTag + ' · L' + a + '–L' + b;
      return '<a class="cite" href="' + href + '">' + label + '</a>';
    }}
  );
  // bare [[raw/...]]
  s = s.replace(/\\[\\[(raw\\/[^\\]]+)\\]\\]/g, (_, path) => {{
    return '<a class="wikilink" href="' + sourceHref(path) + '">[[' + path + ']]</a>';
  }});
  return s;
}}

function renderAnswer(md) {{
  const lines = String(md || '').replace(/\\r\\n/g, '\\n').split('\\n');
  const out = [];
  let inQuote = false;
  let inList = false;
  const closeList = () => {{ if (inList) {{ out.push('</ul>'); inList = false; }} }};
  const closeQuote = () => {{ if (inQuote) {{ out.push('</blockquote>'); inQuote = false; }} }};

  for (const raw of lines) {{
    const line = raw;
    const trimmed = line.trimEnd();
    if (/^>\\s?/.test(trimmed)) {{
      closeList();
      const body = trimmed.replace(/^>\\s?/, '');
      if (!inQuote) {{ out.push('<blockquote>'); inQuote = true; }}
      out.push(linkifyCites(escapeHtml(body)) + '\\n');
      continue;
    }}
    closeQuote();
    const hm = trimmed.match(/^(#{1,3})\\s+(.+)$/);
    if (hm) {{
      closeList();
      const level = hm[1].length;
      out.push('<h' + level + '>' + linkifyCites(escapeHtml(hm[2])) + '</h' + level + '>');
      continue;
    }}
    if (/^[-*]\\s+/.test(trimmed)) {{
      if (!inList) {{ out.push('<ul>'); inList = true; }}
      const item = trimmed.replace(/^[-*]\\s+/, '');
      let htmlItem = escapeHtml(item).replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
      htmlItem = linkifyCites(htmlItem);
      out.push('<li>' + htmlItem + '</li>');
      continue;
    }}
    if (!trimmed) {{
      closeList();
      out.push('');
      continue;
    }}
    closeList();
    let para = escapeHtml(trimmed).replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
    para = linkifyCites(para);
    out.push('<p>' + para + '</p>');
  }}
  closeQuote();
  closeList();
  return out.join('\\n');
}}

async function ask() {{
  const q = (qEl.value || '').trim();
  if (!q) {{
    statusEl.textContent = 'Enter a question.';
    statusEl.className = 'err';
    return;
  }}
  askBtn.disabled = true;
  statusEl.className = '';
  statusEl.textContent = 'Running… (LLM may take a while)';
  answerCard.hidden = true;
  sourcesCard.hidden = true;
  try {{
    const res = await fetch('/ask', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ q }}),
    }});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    answerEl.innerHTML = renderAnswer(data.answer || '(empty)');
    answerCard.hidden = false;
    const sources = data.sources || [];
    if (sources.length) {{
      sourcesEl.innerHTML = sources.map(s => {{
        const id = s.id || (s.path + '#p' + s.para);
        const start = (s.lines && s.lines[0]) || s.start_line;
        const end = (s.lines && s.lines[1]) || s.end_line;
        let href = '/source?id=' + encodeURIComponent(id);
        if (start) href += '&start=' + start + '&end=' + (end || start) + '#L' + start;
        const label = id + (start ? (' · L' + start + '–L' + (end || start)) : '');
        return '<a href="' + href + '">' + escapeHtml(label) + '</a>';
      }}).join('');
      sourcesCard.hidden = false;
    }}
    let ok = 'Done';
    if (data.model) ok += ' · ' + data.model;
    if (data.output_path) ok += ' · saved ' + data.output_path;
    statusEl.textContent = ok;
  }} catch (err) {{
    statusEl.textContent = String(err.message || err);
    statusEl.className = 'err';
  }} finally {{
    askBtn.disabled = false;
  }}
}}

askBtn.addEventListener('click', ask);
qEl.addEventListener('keydown', (e) => {{
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') ask();
}});
</script>
"""
    return _html_page("trace", body)


def _resolve_para_id(raw_id: str) -> str:
    pid = unquote(raw_id or "").strip()
    if pid.startswith("self-wiki/"):
        pid = pid[len("self-wiki/") :]
    return pid


def _resolve_raw_file(path_rel: str) -> Path | None:
    rel = path_rel.replace("\\", "/").lstrip("/")
    if rel.startswith("self-wiki/"):
        rel = rel[len("self-wiki/") :]
    candidates = [
        WORKSPACE_PATH / "self-wiki" / rel,
        RAW_DIR / rel.removeprefix("raw/"),
        WORKSPACE_PATH / rel,
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def _parse_int(vals: list[str] | None) -> int | None:
    if not vals:
        return None
    try:
        return int(vals[0])
    except ValueError:
        return None


def _render_code_lines(
    lines: list[str],
    *,
    start: int,
    end: int,
    focus_start: int | None,
    focus_end: int | None,
) -> str:
    chunks: list[str] = ['<div class="code-view">']
    hi_a = focus_start or 0
    hi_b = focus_end or 0
    for i in range(start, end + 1):
        text = lines[i - 1] if 0 < i <= len(lines) else ""
        cls = "line hi" if hi_a and hi_a <= i <= hi_b else "line"
        chunks.append(
            f'<div class="{cls}" id="L{i}">'
            f'<div class="ln">{i}</div>'
            f'<div class="tx">{html.escape(text)}</div>'
            f"</div>"
        )
    chunks.append("</div>")
    return "\n".join(chunks)


def _source_page(
    *,
    path_rel: str,
    para: dict[str, Any] | None,
    start: int | None,
    end: int | None,
) -> bytes:
    focus_start = start or (int(para["start_line"]) if para and para.get("start_line") else None)
    focus_end = end or (int(para["end_line"]) if para and para.get("end_line") else focus_start)
    file_path = _resolve_raw_file(path_rel)
    title = para["id"] if para else path_rel
    meta_bits = [f"<code>{html.escape(path_rel)}</code>"]
    if para:
        meta_bits.append(f"#{html.escape(str(para.get('id', '')).split('#')[-1])}")
        meta_bits.append(f"kind={html.escape(str(para.get('kind')))}")
    if focus_start:
        meta_bits.append(f"L{focus_start}–L{focus_end or focus_start}")

    if not file_path:
        excerpt = ""
        if para and para.get("text"):
            excerpt = f"<blockquote>{html.escape(para['text'])}</blockquote>"
        body = f"""
<h1>trace source</h1>
<p class="meta">{" · ".join(meta_bits)} · file missing on disk</p>
{excerpt}
<p class="nav"><a href="/">home</a> · <a href="/health">health</a></p>
"""
        return _html_page(title, body)

    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if focus_start:
        win_start = max(1, focus_start - _CTX_LINES)
        win_end = min(len(lines), (focus_end or focus_start) + _CTX_LINES)
    else:
        win_start, win_end = 1, min(len(lines), 80)

    code = _render_code_lines(
        lines,
        start=win_start,
        end=win_end,
        focus_start=focus_start,
        focus_end=focus_end,
    )
    jump = f"#L{focus_start}" if focus_start else ""
    body = f"""
<h1>trace source</h1>
<p class="meta">{" · ".join(meta_bits)} · on disk</p>
{code}
<p class="nav"><a href="/">home</a> · <a href="/health">health</a>
{" · <a href='" + jump + "'>jump to highlight</a>" if focus_start else ""}</p>
<script>
const el = document.getElementById({json.dumps(f"L{focus_start}" if focus_start else "")});
if (el) el.scrollIntoView({{ block: 'center', behavior: 'instant' }});
</script>
"""
    return _html_page(title, body)


class TraceHandler(BaseHTTPRequestHandler):
    server_version = "trace/1.0"

    def log_message(self, fmt: str, *args) -> None:
        logger.info("%s - " + fmt, self.address_string(), *args)

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            idx = ensure_index()
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "trace",
                    "paragraph_count": idx.get("paragraph_count"),
                    "built_at": idx.get("built_at"),
                },
            )
            return

        if parsed.path == "/":
            accept = self.headers.get("Accept", "")
            idx = ensure_index()
            if "application/json" in accept and "text/html" not in accept:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "service": "trace",
                        "paragraph_count": idx.get("paragraph_count"),
                        "built_at": idx.get("built_at"),
                        "ask": 'POST /ask {"q": "..."}',
                    },
                )
                return
            self._send(
                200,
                _home_page(
                    paragraph_count=idx.get("paragraph_count"),
                    built_at=idx.get("built_at"),
                ),
                "text/html; charset=utf-8",
            )
            return

        if parsed.path == "/source":
            qs = parse_qs(parsed.query)
            para_id = _resolve_para_id((qs.get("id") or [""])[0])
            start = _parse_int(qs.get("start"))
            end = _parse_int(qs.get("end"))
            if not para_id:
                self._send_json(400, {"error": "missing id"})
                return
            if "#" not in para_id and qs.get("p"):
                para_id = f"{para_id}#p{qs['p'][0].lstrip('p#')}"

            para = get_paragraph(para_id) if "#" in para_id else None
            if para_id and "#" in para_id and not para:
                ensure_index(force=False)
                para = get_paragraph(para_id)

            path_rel = para["path"] if para else para_id.split("#", 1)[0]
            if not para and "#" in para_id and not start:
                accept = self.headers.get("Accept", "")
                if "text/html" in accept or "text/html" in self.headers.get("Accept", "*/*"):
                    body = _html_page(
                        "Not found",
                        f"<h1>Source not found</h1><p class='meta'>{html.escape(para_id)}</p>"
                        f"<p class='nav'><a href='/'>home</a></p>",
                    )
                    self._send(404, body, "text/html; charset=utf-8")
                else:
                    self._send_json(404, {"error": "not found", "id": para_id})
                return

            accept = self.headers.get("Accept", "")
            if "application/json" in accept and "text/html" not in accept:
                if para:
                    self._send_json(200, para)
                else:
                    self._send_json(
                        200,
                        {"path": path_rel, "start_line": start, "end_line": end},
                    )
                return

            page = _source_page(path_rel=path_rel, para=para, start=start, end=end)
            self._send(200, page, "text/html; charset=utf-8")
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/ask":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return
        q = (payload.get("q") or payload.get("query") or "").strip()
        if not q:
            self._send_json(400, {"error": "missing q"})
            return
        debug = bool(payload.get("debug_retrieval"))
        try:
            result = run_trace(q, debug_retrieval=debug, save=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("trace /ask failed")
            self._send_json(500, {"error": str(exc)})
            return
        self._send_json(
            200,
            {
                "answer": result["answer"],
                "sources": result.get("sources") or [],
                "output_path": result.get("output_path"),
                "language": result.get("language"),
                "query_terms": result.get("query_terms"),
                "provider": result.get("provider"),
                "model": result.get("model"),
            },
        )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="trace HTTP service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    args = parser.parse_args()
    ensure_index()
    httpd = ThreadingHTTPServer((args.host, args.port), TraceHandler)
    logger.info("trace listening on http://%s:%s", args.host, args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
