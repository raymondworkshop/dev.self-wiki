"""Shared LLM provider adapter for self-wiki scripts.

Local MLX/OpenAI-compatible endpoints are the default because this repo may
contain private personal notes. Cloud providers should be explicit opt-ins.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def load_env(env_path: Path | None = None) -> None:
    """Load key=value pairs from .env into os.environ."""

    path = env_path or Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def provider_name(provider: str | None = None) -> str:
    load_env()
    return (provider or os.environ.get("LLM_PROVIDER", "mlx")).lower()


def context_limits(provider: str | None = None) -> tuple[int, int, int]:
    """Return max context, reserved output, and max prompt token budgets."""

    current = provider_name(provider)
    if current == "gemini":
        max_context = int(os.environ.get("MAX_CONTEXT_TOKENS", "100000"))
        reserved_output = int(os.environ.get("RESERVED_OUTPUT_TOKENS", "4096"))
    else:
        max_context = int(os.environ.get("MAX_CONTEXT_TOKENS", "8092"))
        reserved_output = int(os.environ.get("RESERVED_OUTPUT_TOKENS", "1200"))
    margin = int(os.environ.get("PROMPT_SAFETY_MARGIN", "500"))
    max_prompt = max(1024, max_context - reserved_output - margin)
    return max_context, reserved_output, max_prompt


def model_name(provider: str | None = None) -> str:
    current = provider_name(provider)
    if current == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
    return os.environ.get("LLM_MODEL", "mlx-model")


def get_gemini_response(
    messages: List[Dict[str, str]],
    *,
    max_output_tokens: int | None = None,
) -> str | None:
    """Call Google Gemini API via REST."""

    load_env()
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
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
            "maxOutputTokens": max_output_tokens or 4096,
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

    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        if "candidates" not in data or not data["candidates"]:
            logger.error("Gemini API returned no candidates.")
            return None
        candidate = data["candidates"][0]
        if candidate.get("finishReason") == "SAFETY":
            return "Error: Response blocked by Gemini safety filters."
        return candidate["content"]["parts"][0]["text"]
    except Exception as exc:
        logger.error(f"Gemini API Error: {exc}")
        return None


def get_openai_compatible_response(
    messages: List[Dict[str, str]],
    *,
    max_tokens: int | None = None,
) -> str | None:
    """Call MLX, DeepSeek, or any OpenAI-compatible chat endpoint."""

    load_env()
    url = os.environ.get("LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or "no-key"
    )
    payload = {
        "model": os.environ.get("LLM_MODEL", "mlx-model"),
        "messages": messages,
        "temperature": 0.1,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=360)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error(f"LLM Error ({provider_name()} at {url}): {exc}")
        return None


def get_llm_response(
    messages: List[Dict[str, str]],
    provider: str | None = None,
    *,
    max_tokens: int | None = None,
) -> str | None:
    current = provider_name(provider)
    if current == "gemini":
        return get_gemini_response(messages, max_output_tokens=max_tokens)
    return get_openai_compatible_response(messages, max_tokens=max_tokens)


def call_llm(
    prompt: str,
    system_instruction: str = "",
    *,
    provider: str | None = None,
    max_tokens: int | None = None,
) -> str | None:
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt},
    ]
    return get_llm_response(messages, provider=provider, max_tokens=max_tokens)


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
