"""trace CLI command handlers."""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from config import WORKSPACE_PATH, workspace_relpath
from llm_provider import model_name, provider_for_role
from log_utils import append_log
from prepare_trace import prepare_trace
from trace_engine import run_trace, trace_llm_enabled
from trace_index import build_index

logger = logging.getLogger(__name__)


class TraceRemoteError(RuntimeError):
    """The running Trace service answered, but the ask failed."""


def trace_server_url() -> str:
    return os.environ.get("TRACE_URL", "http://127.0.0.1:8791/trace").rstrip("/")


def _use_local_trace(args: argparse.Namespace) -> bool:
    if getattr(args, "force_index", False):
        return True
    flag = os.environ.get("TRACE_LOCAL", "").strip().lower()
    return flag in ("1", "true", "yes")


def fetch_trace(
    query: str,
    *,
    scope: str | None,
    debug: bool,
    save: bool,
    timeout: float = 120,
) -> dict | None:
    """Ask the already-running Trace process. None if nothing is listening."""
    base = trace_server_url()
    parsed = urlparse(base)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=0.3):
            pass
    except OSError:
        return None
    body = json.dumps(
        {
            "q": query,
            "scope": scope,
            "debug_retrieval": debug,
            "save": save,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/ask",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise TraceRemoteError("trace server returned non-JSON") from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TraceRemoteError(f"trace server {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        logger.info("trace server unreachable (%s); loading locally", exc.reason)
        return None


def cmd_trace_index(args: argparse.Namespace) -> int:
    idx = build_index(force=args.force)
    print(
        f"trace-index: {idx['file_count']} files, {idx['paragraph_count']} paragraphs "
        f"(digest={idx.get('digest')})"
    )
    try:
        from trace_vectors import ensure_vectors

        store = ensure_vectors(idx.get("paragraphs") or [], force=args.force)
        if store is not None:
            print(f"trace-vectors: {len(store.ids)} paragraphs")
        else:
            print("trace-vectors: off")
    except Exception:
        logger.exception("trace vectors unavailable; keyword index is ready")
    verb = "rebuilt" if args.force else "updated"
    append_log(
        "trace-index",
        f"{verb} log/trace-index.json | files={idx['file_count']} paragraphs={idx['paragraph_count']}",
    )
    return 0


def cmd_prepare_trace(args: argparse.Namespace) -> int:
    pending, path = prepare_trace(args.query, provider=args.provider, scope=args.scope)
    logger.info("Prepared trace pending: %s", workspace_relpath(path))
    logger.info(
        "language=%s scope=%s candidates=%s terms=%s",
        pending["language"],
        pending.get("scope") or "(all)",
        len(pending.get("candidates") or []),
        len(pending.get("query_terms") or []),
    )
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    if not _use_local_trace(args):
        try:
            remote = fetch_trace(
                args.query,
                scope=args.scope,
                debug=args.debug_retrieval,
                save=not args.no_save,
            )
        except TraceRemoteError as exc:
            logger.error("%s", exc)
            return 1
        if remote is not None:
            logger.info("trace via %s", trace_server_url())
            print(remote.get("answer") or "")
            if remote.get("output_path"):
                logger.info("Saved to %s", remote["output_path"])
            return 0
    if trace_llm_enabled():
        llm_provider = provider_for_role("trace", args.provider)
        logger.info(
            "trace LLM: provider=%s model=%s",
            llm_provider,
            model_name(llm_provider, role="trace"),
        )
    else:
        logger.info("trace retrieval (no answer LLM)")
    result = run_trace(
        args.query,
        provider=args.provider,
        debug_retrieval=args.debug_retrieval,
        save=not args.no_save,
        force_index=args.force_index,
        scope=args.scope,
    )
    print(result["answer"])
    if result.get("output_path"):
        logger.info("Saved to %s", result["output_path"])
    return 0
