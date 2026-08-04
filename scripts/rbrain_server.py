"""Thin rbrain HTTP service: POST /ask, GET /source, GET /health (stdlib only)."""

from __future__ import annotations

import argparse
import html
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config import RAW_DIR, WORKSPACE_PATH
from rbrain_engine import run_rbrain
from rbrain_index import ensure_index, get_paragraph

logger = logging.getLogger(__name__)


def _html_page(title: str, body: str) -> bytes:
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
body {{ font-family: ui-sans-serif, system-ui, sans-serif; max-width: 52rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
pre, blockquote {{ background: #f4f4f5; padding: 0.75rem 1rem; border-radius: 6px; white-space: pre-wrap; }}
code {{ font-size: 0.9em; }}
.meta {{ color: #52525b; font-size: 0.9rem; }}
a {{ color: #1d4ed8; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
    return doc.encode("utf-8")


def _resolve_para_id(raw_id: str) -> str:
    pid = unquote(raw_id or "").strip()
    if pid.startswith("self-wiki/"):
        pid = pid[len("self-wiki/") :]
    return pid


class RbrainHandler(BaseHTTPRequestHandler):
    server_version = "rbrain/1.0"

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
        if parsed.path in ("/", "/health"):
            idx = ensure_index()
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "rbrain",
                    "paragraph_count": idx.get("paragraph_count"),
                    "built_at": idx.get("built_at"),
                },
            )
            return

        if parsed.path == "/source":
            qs = parse_qs(parsed.query)
            para_id = _resolve_para_id((qs.get("id") or [""])[0])
            if not para_id:
                self._send_json(400, {"error": "missing id"})
                return
            # Accept id with or without fragment split across query
            if "#" not in para_id and qs.get("p"):
                para_id = f"{para_id}#{qs['p'][0]}"
            para = get_paragraph(para_id)
            if not para:
                # try ensuring fresh index once
                ensure_index(force=False)
                para = get_paragraph(para_id)
            if not para:
                accept = self.headers.get("Accept", "")
                if "text/html" in accept:
                    body = _html_page(
                        "Not found",
                        f"<h1>Source not found</h1><p class='meta'>{html.escape(para_id)}</p>",
                    )
                    self._send(404, body, "text/html; charset=utf-8")
                else:
                    self._send_json(404, {"error": "not found", "id": para_id})
                return

            accept = self.headers.get("Accept", "")
            if "application/json" in accept and "text/html" not in accept:
                self._send_json(200, para)
                return

            abs_path = WORKSPACE_PATH / "self-wiki" / para["path"]
            if not abs_path.exists():
                abs_path = RAW_DIR / para["path"].removeprefix("raw/")
            exists = abs_path.exists()
            body = _html_page(
                para["id"],
                f"""
<h1>rbrain source</h1>
<p class="meta">
  <code>{html.escape(para['id'])}</code><br/>
  file: <code>{html.escape(para['file'])}</code> ·
  lines L{para['start_line']}–L{para['end_line']} ·
  kind: {html.escape(str(para.get('kind')))}
</p>
<p class="meta">path: <code>{html.escape(para['path'])}</code>
{" · on disk" if exists else " · file missing on disk"}</p>
<blockquote>{html.escape(para['text'])}</blockquote>
<p><a href="/health">health</a></p>
""",
            )
            self._send(200, body, "text/html; charset=utf-8")
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
            result = run_rbrain(q, debug_retrieval=debug, save=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("rbrain /ask failed")
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
    parser = argparse.ArgumentParser(description="rbrain HTTP service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    args = parser.parse_args()
    ensure_index()
    httpd = ThreadingHTTPServer((args.host, args.port), RbrainHandler)
    logger.info("rbrain listening on http://%s:%s", args.host, args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
