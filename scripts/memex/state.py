from __future__ import annotations

from typing import Any

_ctx: dict[str, Any] | None = None


def get_ctx() -> dict[str, Any]:
    if _ctx is None:
        raise RuntimeError("memex context not built; call build_memex_context() first")
    return _ctx


def set_ctx(ctx: dict[str, Any]) -> None:
    global _ctx
    _ctx = ctx


def try_get_ctx() -> dict[str, Any] | None:
    return _ctx
