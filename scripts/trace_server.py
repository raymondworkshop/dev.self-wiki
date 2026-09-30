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
STATIC_DIR = Path(__file__).resolve().parent / "trace_static"
_STATIC_FILES = {
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/icon-192.png": ("icon-192.png", "image/png"),
    "/icon-512.png": ("icon-512.png", "image/png"),
    "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
}


def _html_page(title: str, body: str, *, extra_head: str = "") -> bytes:
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#1c1917"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="default"/>
<meta name="apple-mobile-web-app-title" content="Trace"/>
<meta name="description" content="Ask your raw notes — verbatim cites only. Peer product to Echo."/>
<link rel="manifest" href="/manifest.webmanifest"/>
<link rel="icon" href="/favicon.svg" type="image/svg+xml"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
<title>{html.escape(title)}</title>
<style>
:root {{
  color-scheme: light;
  --ink: #1c1917;
  --muted: #78716c;
  --soft: #a8a29e;
  --line: #e7e5e4;
  --bg: #f7f5f2;
  --card: #fffcf9;
  --accent: #0f766e;
  --quote: #f0ebe3;
  --hi: #fde68a;
  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "PingFang SC", "Hiragino Sans GB", "Helvetica Neue", "Helvetica", "Arial", sans-serif;
  --serif: "New York", "Iowan Old Style", "Songti SC", "STSong", "PingFang SC", ui-serif, Georgia, serif;
  --mono: "SF Mono", ui-monospace, Menlo, Monaco, monospace;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: var(--sans);
  max-width: 44rem;
  margin: 0 auto;
  padding: 2.5rem 1.35rem 4rem;
  padding-top: calc(2.5rem + env(safe-area-inset-top, 0px));
  padding-bottom: calc(4rem + env(safe-area-inset-bottom, 0px));
  line-height: 1.7;
  font-size: 17px;
  color: var(--ink);
  background:
    radial-gradient(1200px 500px at 50% -10%, #fff 0%, transparent 55%),
    var(--bg);
  -webkit-font-smoothing: antialiased;
  -webkit-tap-highlight-color: transparent;
}}
h1.brand {{
  font-family: var(--sans);
  font-size: 1.35rem;
  font-weight: 650;
  letter-spacing: -0.03em;
  margin: 0;
}}
.products {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  margin: 0 0 0.5rem;
}}
.products a, .products .brand {{
  padding: 0.35rem 0.65rem;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 650;
  letter-spacing: 0.03em;
}}
.products a {{
  color: var(--muted);
  font-size: 1.05rem;
}}
.products a:hover {{
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, white);
}}
.products .brand.is-active {{
  color: var(--ink);
  background: color-mix(in srgb, var(--accent) 10%, white);
  font-size: 1.15rem;
}}
.meta {{
  color: var(--muted);
  font-size: 0.95rem;
  margin: 0 0 1.75rem;
  font-family: var(--sans);
  font-weight: 400;
}}
.meta a {{ color: var(--muted); }}
.peer {{
  display: none;
}}
.a2hs {{
  display: none;
  align-items: flex-start;
  gap: 0.75rem;
  margin: 0 0 1.25rem;
  padding: 0.75rem 1rem;
  background: color-mix(in srgb, var(--accent) 8%, white);
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 0.9rem;
  color: var(--ink);
  line-height: 1.45;
}}
.a2hs p {{ margin: 0; flex: 1; }}
.a2hs button {{
  appearance: none;
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  padding: 0.1rem 0.35rem;
}}
label {{
  display: block;
  font-family: var(--sans);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--muted);
  margin-bottom: 0.45rem;
  letter-spacing: 0.02em;
}}
textarea {{
  width: 100%;
  min-height: 5.5rem;
  padding: 0.95rem 1.05rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  font: inherit;
  font-size: 1.12rem;
  background: var(--card);
  resize: vertical;
  box-shadow: 0 1px 0 rgba(28,25,23,.03);
}}
textarea:focus {{ outline: 2px solid color-mix(in srgb, var(--accent) 35%, white); outline-offset: 1px; border-color: color-mix(in srgb, var(--accent) 40%, var(--line)); }}
.hint {{ margin: 0.45rem 0 0; font-size: 0.88rem; color: var(--soft); font-family: var(--sans); }}
.model-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem 1.1rem;
  align-items: center;
  margin: 0.85rem 0 0.25rem;
  font-size: 0.95rem;
  color: var(--muted);
}}
.model-row legend {{
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--muted);
  padding: 0;
  margin: 0 0.35rem 0 0;
}}
.model-row label.pick {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  color: var(--ink);
  font-weight: 500;
  cursor: pointer;
  letter-spacing: 0;
}}
.model-row input {{
  accent-color: var(--accent);
}}
.model-hint {{
  width: 100%;
  margin: 0;
  font-size: 0.82rem;
  color: var(--soft);
}}
.row {{
  display: flex;
  gap: 0.85rem;
  align-items: center;
  margin-top: 0.95rem;
  flex-wrap: wrap;
  font-family: var(--sans);
}}
button {{
  background: var(--ink);
  color: #fafaf9;
  border: 0;
  border-radius: 999px;
  padding: 0.65rem 1.4rem;
  font: inherit;
  font-family: var(--sans);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: transform .12s ease, opacity .12s ease;
}}
button:hover {{ transform: translateY(-1px); }}
button:disabled {{ opacity: 0.5; cursor: wait; transform: none; }}
#status {{ color: var(--muted); font-size: 0.92rem; }}
#status.err {{ color: #b91c1c; }}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
.card {{
  background: transparent;
  border: 0;
  border-radius: 0;
  padding: 0;
  margin-top: 2.25rem;
  box-shadow: none;
}}
.card + .card {{ margin-top: 1.75rem; padding-top: 1.5rem; border-top: 1px solid var(--line); }}
.card > .sec-label {{
  font-family: var(--sans);
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--soft);
  margin: 0 0 1rem;
  font-weight: 600;
}}
#answer.prose {{ white-space: normal; font-size: 1.12rem; font-family: var(--sans); }}
#answer.prose > .lead {{
  font-size: 1.22rem;
  line-height: 1.55;
  color: #44403c;
  margin: 0 0 1.35rem;
  padding: 0;
  border: 0;
  background: none;
  font-style: italic;
}}
#answer.prose h1 {{ display: none; }} /* question already in the form */
#answer.prose h2, #answer.prose h3 {{
  font-family: var(--sans);
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 1.5rem 0 0.55rem;
  line-height: 1.3;
  color: var(--ink);
}}
#answer.prose h2 {{ font-size: 1.05rem; }}
#answer.prose h2.answer-h {{ display: none; }} /* section chrome redundant with card label */
#answer.prose h3 {{ font-size: 1rem; color: #57534e; }}
#answer.prose p {{ margin: 0.65rem 0; }}
#answer.prose ul {{ margin: 0.35rem 0 0.9rem; padding-left: 1.15rem; }}
#answer.prose li {{ margin: 0.45rem 0; padding-left: 0.15rem; }}
#answer.prose li::marker {{ color: var(--soft); }}
#answer.prose blockquote {{
  margin: 0.55rem 0 0.85rem;
  padding: 0.75rem 1rem;
  border-left: 2px solid #d6d3d1;
  background: var(--quote);
  border-radius: 0 10px 10px 0;
  color: #44403c;
  font-size: 1.05rem;
  line-height: 1.55;
  white-space: pre-wrap;
}}
#answer.prose .cite, #answer.prose .wikilink {{
  font-family: var(--sans);
  font-size: 0.82em;
  font-weight: 500;
  color: var(--accent);
  background: transparent;
  padding: 0;
  border-bottom: 1px dotted color-mix(in srgb, var(--accent) 45%, transparent);
  border-radius: 0;
  white-space: nowrap;
}}
#answer.prose .cite:hover, #answer.prose .wikilink:hover {{
  background: transparent;
  border-bottom-style: solid;
}}
#answer.prose strong {{ font-weight: 600; }}
#answer.prose details.prov {{
  margin-top: 1.75rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--line);
  font-size: 1.02rem;
}}
#answer.prose details.prov > summary {{
  font-family: var(--sans);
  font-size: 0.88rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--soft);
  cursor: pointer;
  list-style: none;
  user-select: none;
}}
#answer.prose details.prov > summary::-webkit-details-marker {{ display: none; }}
#answer.prose details.prov > summary::after {{ content: " · collapse"; font-weight: 400; letter-spacing: 0; text-transform: none; }}
#answer.prose details.prov:not([open]) > summary::after {{ content: " · expand"; }}
#answer.prose details.prov .prov-body {{ margin-top: 0.85rem; color: #57534e; }}
#sources {{
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}}
#sources a {{
  font-family: var(--sans);
  font-size: 0.95rem;
  color: #57534e;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--line);
}}
#sources a:last-child {{ border-bottom: 0; }}
#sources a:hover {{ color: var(--accent); }}
details.sources-wrap > summary {{
  font-family: var(--sans);
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--soft);
  font-weight: 600;
  cursor: pointer;
  list-style: none;
  margin-bottom: 0.75rem;
}}
details.sources-wrap > summary::-webkit-details-marker {{ display: none; }}
details.sources-wrap > summary::after {{ content: " · collapse"; font-weight: 400; letter-spacing: 0; text-transform: none; }}
details.sources-wrap:not([open]) > summary::after {{ content: " · expand"; }}
.code-view {{ font-family: var(--mono); font-size: 0.9rem; line-height: 1.45; border: 1px solid var(--line); border-radius: 10px; overflow: auto; background: #fff; max-height: 75vh; }}
.code-view .line {{ display: grid; grid-template-columns: 3.5rem 1fr; gap: 0.75rem; padding: 0 0.75rem; }}
.code-view .line:hover {{ background: #f5f5f4; }}
.code-view .ln {{ color: var(--muted); text-align: right; user-select: none; padding: 0.15rem 0; }}
.code-view .tx {{ white-space: pre-wrap; word-break: break-word; padding: 0.15rem 0; }}
.code-view .line.hi {{ background: var(--hi); }}
.code-view .line.hi .ln {{ color: #92400e; font-weight: 700; }}
.nav {{ font-family: var(--sans); margin-top: 1.25rem; font-size: 1rem; }}
@media (max-width: 560px) {{
  body {{ padding: 1.5rem 1rem 3rem; font-size: 16px; }}
  #answer.prose {{ font-size: 1.06rem; }}
}}
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
<nav class="products" aria-label="Products">
  <a href="http://100.90.225.26:5050/">Echo</a>
  <span class="brand is-active">Trace</span>
</nav>
<p class="meta">verbatim raw Q&amp;A · {meta} · default gpt</p>
<div class="a2hs" id="a2hs" role="status">
  <p>Add to Home Screen: Share <span aria-hidden="true">□↑</span> → <strong>Add to Home Screen</strong></p>
  <button type="button" id="a2hs-dismiss" aria-label="Dismiss">×</button>
</div>
<label for="q">Question</label>
<textarea id="q" placeholder="什麼是自由？愛呢？"></textarea>
<label for="scope" style="margin-top:1rem">Scope (optional)</label>
<input id="scope" type="text" placeholder="a-free-man  or  raw/_posts/2026-03-01-a-free-man.md" style="width:100%;padding:0.75rem 1rem;border:1px solid var(--line);border-radius:12px;font:inherit;font-size:1rem;background:var(--card)"/>
<label for="upload" style="margin-top:1rem">Upload (optional)</label>
<div class="row" style="margin-top:0.35rem;gap:0.75rem;align-items:center">
  <input id="upload" type="file" accept=".md,.markdown,.txt,.text,text/plain,text/markdown"/>
  <button id="uploadClear" type="button" style="display:none">Clear file</button>
</div>
<p id="uploadMeta" class="hint" style="margin-top:0.35rem"></p>
<fieldset class="model-row" id="modelRow">
  <legend>Model</legend>
  <label class="pick"><input type="radio" name="model" value="gpt" checked/> gpt <span style="color:var(--soft);font-weight:400">(cloud · faster on long packs)</span></label>
  <label class="pick"><input type="radio" name="model" value="mlx"/> mlx <span style="color:var(--soft);font-weight:400">(local · private)</span></label>
  <p class="model-hint">Choice is remembered on this device.</p>
</fieldset>
<p class="hint">Leave scope empty for all raw/ · or @a-free-man · or upload .md/.txt (temp, not saved to vault) · Enter to ask</p>
<div class="row">
  <button id="ask" type="button">Ask</button>
  <span id="status"></span>
</div>
<div id="answerCard" class="card" hidden>
  <div class="sec-label">Answer</div>
  <div id="answer" class="prose"></div>
</div>
<div id="sourcesCard" class="card" hidden>
  <details class="sources-wrap" open>
    <summary>Retrieval candidates</summary>
    <div id="sources"></div>
  </details>
</div>
<script>
(function () {{
  try {{
    if (sessionStorage.getItem('trace-hide-a2hs') === '1') return;
  }} catch (e) {{}}
  const ua = navigator.userAgent || '';
  const iOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const standalone = window.navigator.standalone === true;
  const safari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
  if (iOS && safari && !standalone) {{
    const el = document.getElementById('a2hs');
    if (el) el.style.display = 'flex';
  }}
  document.getElementById('a2hs-dismiss')?.addEventListener('click', () => {{
    const el = document.getElementById('a2hs');
    if (el) el.style.display = 'none';
    try {{ sessionStorage.setItem('trace-hide-a2hs', '1'); }} catch (e) {{}}
  }});
}})();
</script>
<script>
const qEl = document.getElementById('q');
const scopeEl = document.getElementById('scope');
const uploadEl = document.getElementById('upload');
const uploadClearBtn = document.getElementById('uploadClear');
const uploadMetaEl = document.getElementById('uploadMeta');
const askBtn = document.getElementById('ask');
const statusEl = document.getElementById('status');
const answerEl = document.getElementById('answer');
const answerCard = document.getElementById('answerCard');
const sourcesEl = document.getElementById('sources');
const sourcesCard = document.getElementById('sourcesCard');

let uploadText = null;
let uploadName = null;
const MAX_UPLOAD_BYTES = 1500000;

function setUploadMeta(msg) {{
  if (uploadMetaEl) uploadMetaEl.textContent = msg || '';
  if (uploadClearBtn) uploadClearBtn.style.display = uploadText ? 'inline-block' : 'none';
}}

function clearUpload() {{
  uploadText = null;
  uploadName = null;
  if (uploadEl) uploadEl.value = '';
  setUploadMeta('');
}}

uploadEl?.addEventListener('change', async () => {{
  const f = uploadEl.files && uploadEl.files[0];
  if (!f) {{ clearUpload(); return; }}
  if (f.size > MAX_UPLOAD_BYTES) {{
    clearUpload();
    statusEl.textContent = 'File too large (max ~1.5MB text).';
    statusEl.className = 'err';
    return;
  }}
  const name = f.name || 'upload.md';
  if (!/\\.(md|markdown|txt|text)$/i.test(name)) {{
    clearUpload();
    statusEl.textContent = 'Use .md / .txt only.';
    statusEl.className = 'err';
    return;
  }}
  try {{
    uploadText = await f.text();
    uploadName = name;
    setUploadMeta('Loaded ' + name + ' · ' + uploadText.length + ' chars (temp scope; not saved to vault)');
    statusEl.textContent = '';
    statusEl.className = '';
  }} catch (err) {{
    clearUpload();
    statusEl.textContent = String(err.message || err);
    statusEl.className = 'err';
  }}
}});
uploadClearBtn?.addEventListener('click', clearUpload);

function escapeHtml(s) {{
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}}

const SESSION_KEY = 'trace.lastResult';
const MODEL_KEY = 'trace.model';

function selectedModel() {{
  const el = document.querySelector('input[name="model"]:checked');
  return (el && el.value) || 'gpt';
}}

function setModel(value) {{
  const v = (value === 'mlx') ? 'mlx' : 'gpt';
  const el = document.querySelector('input[name="model"][value="' + v + '"]');
  if (el) el.checked = true;
}}

(function restoreModel() {{
  try {{
    const saved = localStorage.getItem(MODEL_KEY);
    if (saved) setModel(saved);
    else setModel('gpt');
  }} catch (_) {{
    setModel('gpt');
  }}
  document.querySelectorAll('input[name="model"]').forEach((el) => {{
    el.addEventListener('change', () => {{
      try {{ localStorage.setItem(MODEL_KEY, selectedModel()); }} catch (_) {{}}
    }});
  }});
}})();

function sourceHref(path, pTag, start, end) {{
  const id = pTag ? (path + pTag) : path;
  let href = '/source?id=' + encodeURIComponent(id);
  if (start) href += '&start=' + start;
  if (end) href += '&end=' + end;
  if (start) href += '#L' + start;
  return href;
}}

function sourceLink(href, label, className, title) {{
  const cls = className ? (' class="' + className + '"') : '';
  const tit = title ? (' title="' + escapeHtml(title) + '"') : '';
  return '<a' + cls + ' href="' + href + '" target="_blank" rel="noopener"' + tit + '>' + label + '</a>';
}}

function linkifyCites(escaped) {{
  // Compact cite: show #pN · Lx–Ly; full path in title tooltip.
  let s = escaped.replace(
    /(?:\\(?\\s*(?:Source:\\s*)?)?\\[\\[((?:raw|upload)\\/[^\\]]+)\\]\\]\\s*·\\s*(#p\\d+)\\s*·\\s*L(\\d+)\\s*[–—-]\\s*L?(\\d+)\\)?/g,
    (_, path, pTag, a, b) => {{
      const href = sourceHref(path, pTag, a, b);
      const short = pTag + ' · L' + a + '–' + b;
      return sourceLink(href, short, 'cite', '[[' + path + ']]');
    }}
  );
  s = s.replace(/\\[\\[((?:raw|upload)\\/[^\\]]+)\\]\\]/g, (_, path) => {{
    const leaf = path.split('/').pop() || path;
    return sourceLink(sourceHref(path), leaf, 'wikilink', '[[' + path + ']]');
  }});
  return s;
}}

function renderSources(sources) {{
  return (sources || []).map(s => {{
    const id = s.id || (s.path + '#p' + s.para);
    const start = (s.lines && s.lines[0]) || s.start_line;
    const end = (s.lines && s.lines[1]) || s.end_line;
    let href = '/source?id=' + encodeURIComponent(id);
    if (start) href += '&start=' + start + '&end=' + (end || start) + '#L' + start;
    const leaf = (s.path || id).split('/').pop() || id;
    const label = leaf + (s.para != null ? (' #' + 'p' + s.para) : '') + (start ? (' · L' + start) : '');
    return sourceLink(href, escapeHtml(label), '', id);
  }}).join('');
}}

function showResult(data, {{ persist }} = {{ persist: true }}) {{
  const answer = data.answer || '(empty)';
  answerEl.innerHTML = renderAnswer(answer);
  answerCard.hidden = false;
  const sources = data.sources || [];
  if (sources.length) {{
    sourcesEl.innerHTML = renderSources(sources);
    sourcesCard.hidden = false;
  }} else {{
    sourcesEl.innerHTML = '';
    sourcesCard.hidden = true;
  }}
  let ok = data.status || 'Done';
  if (!data.status) {{
    if (data.scope) ok += ' · scope ' + data.scope;
    if (data.model) ok += ' · ' + data.model;
    if (data.output_path) ok += ' · saved';
  }}
  statusEl.className = '';
  statusEl.textContent = ok;
  if (persist) {{
    try {{
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({{
        q: data.q || qEl.value || '',
        scope: data.scope || (scopeEl && scopeEl.value) || '',
        answer,
        sources,
        model: data.model || '',
        output_path: data.output_path || '',
        status: ok,
      }}));
    }} catch (_) {{}}
  }}
}}

function restoreResult() {{
  try {{
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data.q) qEl.value = data.q;
    if (scopeEl && data.scope != null) scopeEl.value = data.scope;
    showResult(data, {{ persist: false }});
  }} catch (_) {{}}
}}

function formatInline(escaped) {{
  let s = escaped.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
  return linkifyCites(s);
}}

function renderBodyLines(lines) {{
  const out = [];
  let inQuote = false;
  let inList = false;
  let leadDone = false;
  const closeList = () => {{ if (inList) {{ out.push('</ul>'); inList = false; }} }};
  const closeQuote = () => {{ if (inQuote) {{ out.push('</blockquote>'); inQuote = false; }} }};

  for (const raw of lines) {{
    const trimmed = raw.trimEnd();
    if (/^>\\s?/.test(trimmed)) {{
      closeList();
      const body = trimmed.replace(/^>\\s?/, '');
      if (!inQuote) {{
        const cls = !leadDone ? ' class="lead"' : '';
        out.push('<blockquote' + cls + '>');
        inQuote = true;
        if (!leadDone) leadDone = true;
      }}
      out.push(formatInline(escapeHtml(body)) + '\\n');
      continue;
    }}
    closeQuote();
    const hm = trimmed.match(/^(#{1,3})\\s+(.+)$/);
    if (hm) {{
      closeList();
      const level = hm[1].length;
      const title = hm[2].trim();
      const cls = (level === 2 && /^answer$/i.test(title)) ? ' class="answer-h"' : '';
      out.push('<h' + level + cls + '>' + formatInline(escapeHtml(title)) + '</h' + level + '>');
      continue;
    }}
    if (/^[-*]\\s+/.test(trimmed)) {{
      if (!inList) {{ out.push('<ul>'); inList = true; }}
      const item = trimmed.replace(/^[-*]\\s+/, '');
      out.push('<li>' + formatInline(escapeHtml(item)) + '</li>');
      continue;
    }}
    if (!trimmed) {{
      closeList();
      out.push('');
      continue;
    }}
    closeList();
    out.push('<p>' + formatInline(escapeHtml(trimmed)) + '</p>');
  }}
  closeQuote();
  closeList();
  return out.join('\\n');
}}

function renderAnswer(md) {{
  const text = String(md || '').replace(/\\r\\n/g, '\\n');
  const provRe = /^##\\s+Provenance\\s*$/im;
  const m = text.match(provRe);
  let main = text;
  let prov = '';
  if (m && m.index != null) {{
    main = text.slice(0, m.index).trimEnd();
    prov = text.slice(m.index).replace(/^##\\s+Provenance\\s*/i, '').trim();
  }}
  let htmlOut = renderBodyLines(main.split('\\n'));
  if (prov) {{
    htmlOut += '<details class="prov" open><summary>Provenance</summary><div class="prov-body">'
      + renderBodyLines(prov.split('\\n'))
      + '</div></details>';
  }}
  return htmlOut;
}}

async function ask() {{
  const q = (qEl.value || '').trim();
  const scope = (scopeEl && scopeEl.value || '').trim();
  const model = selectedModel();
  if (!q) {{
    statusEl.textContent = 'Enter a question.';
    statusEl.className = 'err';
    return;
  }}
  askBtn.disabled = true;
  statusEl.className = '';
  let thinking = uploadName
    ? ('Thinking in upload/' + uploadName + '…')
    : (scope ? ('Thinking in ' + scope + '…') : 'Thinking…');
  thinking += ' · ' + model;
  statusEl.textContent = thinking;
  answerCard.hidden = true;
  sourcesCard.hidden = true;
  try {{
    const body = {{ q, scope: uploadText ? null : (scope || null), model }};
    if (uploadText) {{
      body.upload = uploadText;
      body.upload_filename = uploadName || 'upload.md';
    }}
    const res = await fetch('/ask', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(body),
    }});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    data.q = q;
    data.scope = data.scope || scope;
    showResult(data);
  }} catch (err) {{
    statusEl.textContent = String(err.message || err);
    statusEl.className = 'err';
  }} finally {{
    askBtn.disabled = false;
  }}
}}

askBtn.addEventListener('click', ask);
qEl.addEventListener('keydown', (e) => {{
  if (e.key === 'Enter' && !e.shiftKey) {{
    e.preventDefault();
    ask();
  }}
}});
restoreResult();
</script>
"""
    return _html_page("Trace", body)


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
        static = _STATIC_FILES.get(parsed.path)
        if static:
            name, ctype = static
            path = STATIC_DIR / name
            if not path.is_file():
                self._send_json(404, {"error": "static missing", "path": name})
                return
            data = path.read_bytes()
            self._send(200, data, ctype)
            return
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
                        "ask": 'POST /ask {"q": "...", "model": "mlx|gpt", "scope"?: "...", "upload"?: "…", "upload_filename"?: "note.md"}',
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
        scope = (payload.get("scope") or payload.get("path") or "").strip() or None
        debug = bool(payload.get("debug_retrieval"))
        model = (payload.get("model") or "").strip() or "gpt"
        upload_text = payload.get("upload") or payload.get("document") or payload.get("text")
        if upload_text is not None:
            upload_text = str(upload_text)
        upload_filename = (
            payload.get("upload_filename")
            or payload.get("filename")
            or payload.get("name")
            or None
        )
        try:
            result = run_trace(
                q,
                debug_retrieval=debug,
                save=True,
                scope=scope,
                model=model,
                upload_text=upload_text,
                upload_filename=upload_filename,
            )
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
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
                "scope": result.get("scope"),
                "scope_paths": result.get("scope_paths") or [],
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
