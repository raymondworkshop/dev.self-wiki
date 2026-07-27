"""Composer-first policy: no local MLX unless explicitly allowed."""

from __future__ import annotations

import os
import sys


def local_llm_allowed() -> bool:
    return os.environ.get("ALLOW_LOCAL_LLM", "0").strip().lower() in {"1", "true", "yes"}


def mlx_last_resort_allowed() -> bool:
    """Allow MLX when cloud fails or is unconfigured (not as deliberate primary)."""
    if local_llm_allowed():
        return True
    return os.environ.get("LLM_MLX_LAST_RESORT", "1").strip().lower() in {"1", "true", "yes"}


def python_llm_ingest_allowed() -> bool:
    return os.environ.get("ALLOW_PYTHON_LLM", "0").strip().lower() in {"1", "true", "yes"}


_LOCAL_GATEWAY_NAMES = frozenset({"mlx", "local-gateway", "local_gateway"})


def reject_local_mlx(provider: str, *, context: str, as_last_resort: bool = False) -> None:
    if provider not in _LOCAL_GATEWAY_NAMES:
        return
    if local_llm_allowed():
        return
    if as_last_resort and mlx_last_resort_allowed():
        return
    raise RuntimeError(
        f"{context}: local-gateway is disabled. "
        "Use Cursor Composer (see AGENTS.md + skills/wiki-synthesize.md), "
        "or cloud API (LLM_PROVIDER=gemini|openai|openrouter). "
        "Override: ALLOW_LOCAL_LLM=1 or LLM_MLX_LAST_RESORT=1"
    )


def reject_python_llm_ingest(*, context: str = "ingest", provider: str | None = None) -> None:
    if python_llm_ingest_allowed():
        return
    if provider and provider not in _LOCAL_GATEWAY_NAMES:
        return
    print(
        "Composer is the default for wiki-synthesize/discovery. Edit wiki in Cursor, "
        "then: make ingest.\n"
        "Cloud batch: ALLOW_PYTHON_LLM=1 make sync  (Gemini, no local-gateway)\n"
        "Manual override: ALLOW_PYTHON_LLM=1 make wiki-synthesize",
        file=sys.stderr,
    )
    raise SystemExit(1)
