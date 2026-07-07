"""Shared LLM provider adapter for self-wiki scripts.

Composer-first: ingest/discovery prefer Composer or cloud; local MLX is last-resort fallback.
Query/lint use cloud API (gemini/openai) when configured.
Local MLX as primary: ALLOW_LOCAL_LLM=1. As fallback when cloud fails: LLM_MLX_LAST_RESORT=1 (default).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List

import requests

from composer_policy import mlx_last_resort_allowed, reject_local_mlx
from config import load_env
from provider_circuit import (
    apply_circuit_breaker,
    is_non_retryable_cloud_error,
    record_provider_failure,
)

logger = logging.getLogger(__name__)
LAST_LLM_ERROR: str | None = None
DEFAULT_MLX_MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
PLACEHOLDER_MODELS = {"", "mlx-model", "local-model"}


def is_rate_limited(error: str | None = None) -> bool:
    text = (error if error is not None else LAST_LLM_ERROR) or ""
    lowered = text.lower()
    return (
        "429" in text
        or "too many requests" in lowered
        or "resource exhausted" in lowered
        or "rate limit" in lowered
    )


def _parse_retry_after(response: requests.Response, default: int) -> int:
    raw = response.headers.get("Retry-After", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return max(1, default)


def provider_name(provider: str | None = None) -> str:
    load_env()
    return (provider or os.environ.get("LLM_PROVIDER", "mlx")).lower()


VALID_PROVIDERS = frozenset({"mlx", "gemini", "openai"})
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def normalize_provider(raw: str | None = None) -> str:
    value = provider_name(raw)
    return value if value in VALID_PROVIDERS else "mlx"


AGENT_ROLES = frozenset({"discover", "discovery", "gap", "evolution"})


def _role_env_key(role: str) -> str | None:
    """Map pipeline role to ``{ROLE}_LLM_PROVIDER`` env var name."""

    mapping = {
        "query": "QUERY_LLM_PROVIDER",
        "lint": "LINT_LLM_PROVIDER",
        "discovery": "DISCOVERY_LLM_PROVIDER",
        "discover": "DISCOVERY_LLM_PROVIDER",
        "gap": "GAP_LLM_PROVIDER",
        "evolution": "EVOLUTION_LLM_PROVIDER",
        "sync": "WIKI_LLM_PROVIDER",
        "ingest": "WIKI_LLM_PROVIDER",
        "wiki_synthesize": "WIKI_LLM_PROVIDER",
        "wiki-synthesize": "WIKI_LLM_PROVIDER",
        "synthesize": "WIKI_LLM_PROVIDER",
    }
    return mapping.get(role or "")


def provider_for_role(role: str | None = None, explicit: str | None = None) -> str:
    """Resolve provider for pipeline role (wiki/query/lint/etc.).

    Priority: explicit CLI arg → ``{ROLE}_LLM_PROVIDER`` → ``AGENT_LLM_PROVIDER``
    (agent roles) → ``QUERY_LLM_PROVIDER`` / ``LINT_LLM_PROVIDER`` → ``LLM_PROVIDER``.
    Agent roles default to ``gemini`` when ``GEMINI_API_KEY`` is set.
    """

    if explicit:
        return normalize_provider(explicit)

    load_env()
    role_key = _role_env_key(role or "")
    if role_key:
        override = os.environ.get(role_key, "").strip()
        if override:
            return normalize_provider(override)

    if role in AGENT_ROLES:
        agent_override = os.environ.get("AGENT_LLM_PROVIDER", "").strip()
        if agent_override:
            return normalize_provider(agent_override)
        if is_provider_configured("gemini"):
            return "gemini"

    return normalize_provider(os.environ.get("LLM_PROVIDER") or "mlx")


def is_provider_configured(provider: str) -> bool:
    """Whether a provider can be called (API key or local endpoint)."""

    load_env()
    name = normalize_provider(provider)
    if name == "mlx":
        return True
    if name == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY", "").strip())
    if name == "openai":
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())
    return False


def fallback_enabled() -> bool:
    load_env()
    return os.environ.get("LLM_FALLBACK_ENABLED", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def fallback_provider_chain(
    primary: str | None = None,
    *,
    role: str | None = None,
) -> list[str]:
    """Primary provider first, then configured fallbacks (deduped).

    Roles:
    - sync / ingest: ``LLM_FALLBACK_PROVIDERS`` (default cloud after mlx)
    - query / lint: ``QUERY_FALLBACK_PROVIDERS`` / ``LINT_FALLBACK_PROVIDERS`` (default mlx)
    """

    load_env()
    role_aware = (
        "query",
        "lint",
        *AGENT_ROLES,
        "sync",
        "ingest",
        "wiki_synthesize",
        "wiki-synthesize",
        "synthesize",
    )
    if role in role_aware:
        primary = provider_for_role(role, primary)
    else:
        primary = normalize_provider(primary)

    if not fallback_enabled():
        return [primary]

    if role in ("query", "lint"):
        explicit = os.environ.get("QUERY_FALLBACK_PROVIDERS", "").strip()
        if role == "lint":
            explicit = os.environ.get("LINT_FALLBACK_PROVIDERS", "").strip() or explicit
        default_candidates = ["gemini", "openai"] if primary != "mlx" else []
    elif role in AGENT_ROLES:
        if primary == "mlx":
            explicit = (
                os.environ.get("AGENT_FALLBACK_PROVIDERS", "").strip()
                or os.environ.get("LLM_FALLBACK_PROVIDERS", "").strip()
            )
            default_candidates = ["gemini", "openai"]
        else:
            explicit = (
                os.environ.get("AGENT_FALLBACK_PROVIDERS", "").strip()
                or os.environ.get("QUERY_FALLBACK_PROVIDERS", "").strip()
            )
            default_candidates = ["gemini", "openai"] if primary != "mlx" else []
    else:
        explicit = os.environ.get("LLM_FALLBACK_PROVIDERS", "").strip()
        default_candidates = ["gemini", "openai"] if primary == "mlx" else []

    if explicit:
        candidates = [
            normalize_provider(part)
            for part in explicit.split(",")
            if part.strip()
        ]
    else:
        candidates = default_candidates

    chain = [primary]
    for candidate in candidates:
        if (
            candidate not in chain
            and is_provider_configured(candidate)
        ):
            chain.append(candidate)

    if mlx_last_resort_allowed() and "mlx" not in chain:
        chain.append("mlx")

    return apply_circuit_breaker(chain)


def context_limits(provider: str | None = None) -> tuple[int, int, int]:
    """Return max context, reserved output, and max prompt token budgets."""

    current = provider_name(provider)
    if current == "gemini":
        max_context = int(os.environ.get("MAX_CONTEXT_TOKENS", "100000"))
        reserved_output = int(os.environ.get("RESERVED_OUTPUT_TOKENS", "4096"))
    elif current == "openai":
        max_context = int(os.environ.get("MAX_CONTEXT_TOKENS", "128000"))
        reserved_output = int(os.environ.get("RESERVED_OUTPUT_TOKENS", "4096"))
    else:
        max_context = int(os.environ.get("MAX_CONTEXT_TOKENS", "8092"))
        reserved_output = int(os.environ.get("RESERVED_OUTPUT_TOKENS", "1200"))
    margin = int(os.environ.get("PROMPT_SAFETY_MARGIN", "500"))
    max_prompt = max(1024, max_context - reserved_output - margin)
    return max_context, reserved_output, max_prompt


def default_output_tokens(provider: str | None = None) -> int:
    """Default completion budget when callers omit max_tokens."""

    _, reserved_output, _ = context_limits(provider)
    return reserved_output


def chat_completions_url(provider: str | None = None) -> str:
    load_env()
    explicit = os.environ.get("LLM_URL", "").strip()
    current = provider_name(provider)
    if current == "openai":
        return explicit or DEFAULT_OPENAI_URL
    return explicit or "http://127.0.0.1:8080/v1/chat/completions"


def openai_compatible_api_base(provider: str | None = None) -> str:
    url = chat_completions_url(provider).rstrip("/")
    suffix = "/chat/completions"
    if url.endswith(suffix):
        return url[: -len(suffix)]
    return url


def resolve_openai_compatible_model(provider: str | None = None) -> str:
    load_env()
    current = provider_name(provider)
    configured = os.environ.get("LLM_MODEL", "").strip()
    if current == "openai":
        openai_model = os.environ.get("OPENAI_MODEL", "").strip()
        if openai_model:
            return openai_model
        if configured and configured not in PLACEHOLDER_MODELS:
            return configured
        return DEFAULT_OPENAI_MODEL

    if configured and configured not in PLACEHOLDER_MODELS:
        return configured

    models_url = f"{openai_compatible_api_base(provider)}/models"
    try:
        response = requests.get(models_url, timeout=5)
        response.raise_for_status()
        models = response.json().get("data", [])
        if models:
            model_id = str(models[0].get("id", "")).strip()
            if model_id:
                logger.info("Auto-selected MLX model: %s", model_id)
                return model_id
    except Exception as exc:
        logger.warning("Could not auto-resolve MLX model from %s: %s", models_url, exc)

    return DEFAULT_MLX_MODEL


def model_name(provider: str | None = None) -> str:
    current = provider_name(provider)
    if current == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
    return resolve_openai_compatible_model(provider)


def format_request_error(
    exc: Exception, *, url: str, provider: str | None = None
) -> str:
    name = provider_name(provider)
    safe_url = url.split("?key=", 1)[0] + "?key=…" if "?key=" in url else url
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            payload = exc.response.json()
            if isinstance(payload, dict) and payload.get("detail"):
                return f"{name} at {safe_url}: {payload['detail']}"
        except Exception:
            pass
        body = (exc.response.text or "").strip()
        if body:
            return f"{name} at {safe_url}: {body[:500]}"
    return f"{name} at {safe_url}: {exc}"


def get_gemini_response(
    messages: List[Dict[str, str]],
    *,
    max_output_tokens: int | None = None,
) -> str | None:
    """Call Google Gemini API via REST."""

    load_env()
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
    if not api_key:
        logger.error("GEMINI_API_KEY not set.")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    system_instruction = None
    contents = []
    for message in messages:
        if message["role"] == "system":
            system_instruction = {"parts": [{"text": message["content"]}]}
        else:
            role = "user" if message["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": message["content"]}]})

    if contents and contents[0]["role"] == "model":
        contents.pop(0)

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": max_output_tokens or default_output_tokens("gemini"),
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    }
    if system_instruction:
        payload["system_instruction"] = system_instruction

    global LAST_LLM_ERROR
    attempts = max(1, int(os.environ.get("GEMINI_RETRY_ATTEMPTS", "4")))
    base_backoff = max(1, int(os.environ.get("GEMINI_RETRY_BACKOFF_SECONDS", "20")))

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(url, json=payload, timeout=300)
            if response.status_code == 429:
                wait = _parse_retry_after(response, base_backoff * attempt)
                LAST_LLM_ERROR = f"429 Too Many Requests (attempt {attempt}/{attempts})"
                if attempt >= attempts:
                    logger.error("Gemini rate limited after %d attempts", attempts)
                    return None
                logger.warning(
                    "Gemini 429 rate limit; sleeping %ss before retry %d/%d",
                    wait,
                    attempt + 1,
                    attempts,
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            if "candidates" not in data or not data["candidates"]:
                logger.error("Gemini API returned no candidates.")
                LAST_LLM_ERROR = "Gemini API returned no candidates"
                return None
            candidate = data["candidates"][0]
            if candidate.get("finishReason") == "SAFETY":
                return "Error: Response blocked by Gemini safety filters."
            LAST_LLM_ERROR = None
            return candidate["content"]["parts"][0]["text"]
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            LAST_LLM_ERROR = format_request_error(exc, url=url, provider="gemini")
            record_provider_failure("gemini", LAST_LLM_ERROR)
            if is_non_retryable_cloud_error(LAST_LLM_ERROR):
                logger.error("Gemini API Error: %s", LAST_LLM_ERROR)
                return None
            if status == 429 and attempt < attempts:
                wait = _parse_retry_after(exc.response, base_backoff * attempt)
                logger.warning(
                    "Gemini 429 rate limit; sleeping %ss before retry %d/%d",
                    wait,
                    attempt + 1,
                    attempts,
                )
                time.sleep(wait)
                continue
            logger.error("Gemini API Error: %s", LAST_LLM_ERROR)
            return None
        except Exception as exc:
            LAST_LLM_ERROR = format_request_error(exc, url=url, provider="gemini")
            record_provider_failure("gemini", LAST_LLM_ERROR)
            logger.error("Gemini API Error: %s", LAST_LLM_ERROR)
            return None
    return None


def get_openai_compatible_response(
    messages: List[Dict[str, str]],
    *,
    max_tokens: int | None = None,
    provider: str | None = None,
) -> str | None:
    """Call MLX, OpenAI cloud, DeepSeek, or any OpenAI-compatible chat endpoint."""

    global LAST_LLM_ERROR
    load_env()
    current = provider_name(provider)
    url = chat_completions_url(provider)
    model = resolve_openai_compatible_model(provider)
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or ("no-key" if current == "mlx" else "")
    )
    if current == "openai" and not api_key:
        logger.error("OPENAI_API_KEY not set.")
        return None
    if max_tokens is None:
        max_tokens = default_output_tokens(provider)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout_seconds = int(os.environ.get("LLM_TIMEOUT_SECONDS", "360"))
    attempts = max(1, int(os.environ.get("LLM_RETRY_ATTEMPTS", "2")))
    backoff_seconds = max(1, int(os.environ.get("LLM_RETRY_BACKOFF_SECONDS", "5")))

    try:
        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                LAST_LLM_ERROR = None
                return data["choices"][0]["message"]["content"]
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt >= attempts:
                    raise exc
                logger.warning(
                    "LLM transient error on attempt %d/%d: %s. Retrying in %ss...",
                    attempt,
                    attempts,
                    exc,
                    backoff_seconds,
                )
                time.sleep(backoff_seconds)
    except Exception as exc:
        LAST_LLM_ERROR = format_request_error(exc, url=url, provider=current)
        if current in ("gemini", "openai"):
            record_provider_failure(current, LAST_LLM_ERROR)
        logger.error("LLM Error: %s", LAST_LLM_ERROR)
        return None


def get_llm_response(
    messages: List[Dict[str, str]],
    provider: str | None = None,
    *,
    max_tokens: int | None = None,
    as_last_resort: bool = False,
) -> str | None:
    current = normalize_provider(provider)
    reject_local_mlx(current, context="LLM call", as_last_resort=as_last_resort)
    if current == "gemini":
        return get_gemini_response(messages, max_output_tokens=max_tokens)
    return get_openai_compatible_response(
        messages, max_tokens=max_tokens, provider=provider
    )


def call_llm(
    prompt: str,
    system_instruction: str = "",
    *,
    provider: str | None = None,
    max_tokens: int | None = None,
    as_last_resort: bool = False,
) -> str | None:
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt},
    ]
    if max_tokens is None:
        max_tokens = default_output_tokens(provider)
    return get_llm_response(
        messages,
        provider=provider,
        max_tokens=max_tokens,
        as_last_resort=as_last_resort,
    )


def extract_json_object(text: str) -> dict | None:
    """Parse a JSON object from raw model text."""

    import re

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
