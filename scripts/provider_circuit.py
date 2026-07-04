"""Skip cloud providers for the rest of a batch after non-retryable failures."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import LOG_DIR, load_env

logger = logging.getLogger(__name__)

CIRCUIT_PATH = LOG_DIR / ".llm_provider_circuit.json"
_SESSION_OPEN: set[str] = set()
_LOGGED_SKIP: set[str] = set()


def is_non_retryable_cloud_error(error: str | None) -> bool:
    text = (error or "").lower()
    return (
        "user location is not supported" in text
        or "failed_precondition" in text
        or "api key not valid" in text
        or "invalid api key" in text
        or "permission denied" in text
        or ("403" in text and "forbidden" in text)
    )


def _circuit_ttl_seconds() -> int:
    load_env()
    return int(os.environ.get("LLM_PROVIDER_CIRCUIT_TTL_SECONDS", "86400"))


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_file() -> dict:
    if not CIRCUIT_PATH.exists():
        return {}
    try:
        return json.loads(CIRCUIT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_file(data: dict) -> None:
    CIRCUIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CIRCUIT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def circuit_reason(provider: str) -> str | None:
    if provider in _SESSION_OPEN:
        entry = _load_file().get(provider, {})
        return entry.get("reason") or "non-retryable failure"
    entry = _load_file().get(provider)
    if not entry:
        return None
    until = entry.get("until")
    if until:
        parsed = _parse_ts(until)
        if parsed and datetime.now(timezone.utc) >= parsed:
            return None
    return entry.get("reason")


def is_circuit_open(provider: str) -> bool:
    return circuit_reason(provider) is not None


def open_provider_circuit(provider: str, reason: str) -> None:
    if is_circuit_open(provider):
        return

    load_env()
    ttl = _circuit_ttl_seconds()
    until = None
    if ttl > 0:
        until = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()

    _SESSION_OPEN.add(provider)
    data = _load_file()
    data[provider] = {
        "reason": (reason or "non-retryable failure")[:240],
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "until": until,
    }
    _save_file(data)
    logger.warning(
        "Provider %s disabled for remaining calls%s: %s",
        provider,
        f" ({ttl}s)" if ttl > 0 else "",
        data[provider]["reason"][:120],
    )


def record_provider_failure(provider: str, error: str | None) -> None:
    if is_non_retryable_cloud_error(error):
        open_provider_circuit(provider, error or "non-retryable failure")


def apply_circuit_breaker(chain: list[str]) -> list[str]:
    filtered = [provider for provider in chain if not is_circuit_open(provider)]
    skipped = [provider for provider in chain if provider not in filtered]
    for provider in skipped:
        if provider not in _LOGGED_SKIP:
            _LOGGED_SKIP.add(provider)
            logger.info(
                "Skipping %s (circuit open): %s",
                provider,
                circuit_reason(provider),
            )
    return filtered or chain


def reset_provider_circuits() -> None:
    """Clear in-memory and persisted circuit state (tests / manual reset)."""

    _SESSION_OPEN.clear()
    _LOGGED_SKIP.clear()
    if CIRCUIT_PATH.exists():
        CIRCUIT_PATH.unlink()
