"""Thin harness: load skill + pending context, call LLM once per skill unit."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import yaml

from config import WORKSPACE_PATH, workspace_relpath
from llm_provider import (
    LAST_LLM_ERROR,
    call_llm,
    default_output_tokens,
    extract_json_object,
    fallback_provider_chain,
    is_rate_limited,
    model_name,
    provider_name,
)
from provider_circuit import is_circuit_open, record_provider_failure

logger = logging.getLogger(__name__)

TEXT_KINDS = frozenset({"query", "lint", "compression", "discovery", "gap", "evolution"})

INGEST_COMPACT_RETRY_SUFFIX = """

CRITICAL (previous response was incomplete JSON):
- Reply with ONE complete JSON object only (no markdown fences).
- At most 2 actions for this chunk.
- summary: max 2 short sentences per action.
- new_body_content: max 400 characters per action; essential bullets only.
"""


def _ingest_output_tokens(provider: str | None, attempt: int) -> int:
    base = int(
        os.environ.get(
            "INGEST_MAX_OUTPUT_TOKENS",
            str(default_output_tokens(provider)),
        )
    )
    if attempt <= 1:
        return base
    return min(base * 2, int(os.environ.get("INGEST_MAX_OUTPUT_TOKENS_CAP", "4096")))


def _run_llm_with_retries(
    *,
    kind: str,
    subject: str,
    user_message: str,
    system_instruction: str,
    provider: str,
    as_last_resort: bool = False,
) -> tuple[str, dict | None]:
    """Call LLM with per-provider parse/empty retries; returns (text, parsed ingest data)."""

    parse_attempts = max(1, int(os.environ.get("INGEST_PARSE_RETRY_ATTEMPTS", "2")))
    response_text = ""
    data: dict | None = None

    for attempt in range(1, parse_attempts + 1):
        prompt = user_message
        max_tokens = None
        if kind == "ingest":
            max_tokens = _ingest_output_tokens(provider, attempt)
            if attempt > 1:
                prompt = user_message + INGEST_COMPACT_RETRY_SUFFIX

        response_text = call_llm(
            prompt,
            system_instruction,
            provider=provider,
            max_tokens=max_tokens,
            as_last_resort=as_last_resort,
        )
        if not response_text:
            record_provider_failure(provider, LAST_LLM_ERROR)
            if is_rate_limited():
                detail = f": {LAST_LLM_ERROR}" if LAST_LLM_ERROR else ""
                raise RuntimeError(f"LLM rate limited{detail}")
            if is_circuit_open(provider):
                detail = f": {LAST_LLM_ERROR}" if LAST_LLM_ERROR else ""
                raise RuntimeError(f"LLM returned empty response{detail}")
            if attempt >= parse_attempts:
                detail = f": {LAST_LLM_ERROR}" if LAST_LLM_ERROR else ""
                raise RuntimeError(f"LLM returned empty response{detail}")
            logger.warning(
                "Empty LLM response for %s via %s on attempt %d/%d; retrying...",
                subject,
                provider,
                attempt,
                parse_attempts,
            )
            continue

        if kind == "ingest":
            data = extract_json_object(response_text)
            if data and "actions" in data:
                return response_text, data
            if attempt >= parse_attempts:
                raise ValueError(
                    f"Invalid skill output (expected actions[]): {response_text[:500]}"
                )
            logger.warning(
                "Malformed ingest JSON for %s via %s on attempt %d/%d; retrying...",
                subject,
                provider,
                attempt,
                parse_attempts,
            )
            continue

        return response_text, None

    return response_text, data


def parse_skill(skill_path: Path) -> tuple[dict, str]:
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2].strip()


def _write_text_output(pending: dict, pending_path: Path, response_text: str) -> Path | None:
    out_name = pending.get("answer_output") or pending.get("output_file")
    if not out_name:
        kind = pending.get("kind", "ingest")
        prefix = (
            "query-answer-"
            if kind == "query"
            else "lint-output-"
            if kind == "lint"
            else "compress-output-"
            if kind == "compression"
            else f"{kind}-output-"
        )
        out_name = pending_path.name.replace(f"{kind}-", prefix, 1).replace(".json", ".md")
    out_path = Path(out_name)
    if not out_path.is_absolute():
        out_path = WORKSPACE_PATH / out_path

    if pending.get("kind") == "compression" and pending.get("raw_path"):
        from apply_compression import apply_compression_text

        raw_rel = pending["raw_path"]
        if not raw_rel.startswith("raw/"):
            raw_rel = f"raw/{raw_rel}"
        return apply_compression_text(
            response_text,
            rel_path=raw_rel,
            out_rel=pending.get("output_file"),
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response_text, encoding="utf-8")
    logger.info("Wrote %s output to %s", pending.get("kind"), workspace_relpath(out_path))
    return out_path


def run_skill_from_pending(
    pending_path: Path,
    *,
    provider: str | None = None,
    write_actions: bool = True,
    write_output: bool | None = None,
) -> dict:
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    kind = pending.get("kind", "ingest")
    skill_rel = pending.get("skill", "skills/wiki-synthesize.md")
    skill_path = WORKSPACE_PATH / skill_rel
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")

    _, system_instruction = parse_skill(skill_path)
    user_message = pending.get("user_message")
    if not user_message:
        raise ValueError(f"pending file missing user_message: {pending_path}")

    subject = pending.get("raw_path") or pending.get("query") or pending_path.name
    skill_role = (
        "query"
        if kind == "query"
        else "lint"
        if kind == "lint"
        else "discovery"
        if kind == "discovery"
        else kind
        if kind in ("gap", "evolution")
        else "sync"
        if kind in ("ingest", "compression")
        else "sync"
    )
    providers = fallback_provider_chain(provider, role=skill_role)
    logger.info(
        "Running skill %s (%s) via %s for %s",
        skill_rel,
        kind,
        " → ".join(providers),
        subject,
    )

    response_text = ""
    data = None
    last_exc: Exception | None = None

    for index, active_provider in enumerate(providers):
        if index > 0:
            logger.warning(
                "Falling back to %s for %s after %s failed",
                active_provider,
                subject,
                providers[index - 1],
            )
        logger.info(
            "LLM call: provider=%s model=%s for %s",
            active_provider,
            model_name(active_provider),
            subject,
        )
        try:
            as_last_resort = active_provider == "mlx" and index > 0
            response_text, data = _run_llm_with_retries(
                kind=kind,
                subject=subject,
                user_message=user_message,
                system_instruction=system_instruction,
                provider=active_provider,
                as_last_resort=as_last_resort,
            )
            if index > 0:
                logger.info("Recovered %s using fallback provider %s", subject, active_provider)
            break
        except Exception as exc:
            last_exc = exc
            record_provider_failure(active_provider, LAST_LLM_ERROR or str(exc))
            if index >= len(providers) - 1:
                raise
            logger.warning(
                "Provider %s failed for %s: %s",
                active_provider,
                subject,
                exc,
            )
    else:
        if last_exc:
            raise last_exc
        raise RuntimeError("LLM call failed with no providers configured")

    should_write = write_output if write_output is not None else write_actions

    if kind == "compression" and pending.get("batch"):
        if not data or "digests" not in data:
            batch_data = extract_json_object(response_text)
        else:
            batch_data = data
        out_path = None
        batch_paths: list[str] = []
        if should_write and batch_data:
            from apply_compression import apply_batch_digests

            paths = apply_batch_digests(batch_data)
            batch_paths = [workspace_relpath(p) for p in paths]
            out_path = paths[0] if paths else None
        return {
            "text": response_text,
            "kind": kind,
            "batch_paths": batch_paths,
            "output_path": workspace_relpath(out_path) if out_path else None,
        }

    if kind in TEXT_KINDS:
        out_path = None
        if should_write:
            out_path = _write_text_output(pending, pending_path, response_text)
        return {
            "text": response_text,
            "kind": kind,
            "output_path": workspace_relpath(out_path) if out_path else None,
        }

    if kind != "ingest":
        raise ValueError(f"Unknown skill kind: {kind}")

    if not data or "actions" not in data:
        raise ValueError(f"Invalid skill output (expected actions[]): {response_text[:500]}")

    if pending.get("raw_path"):
        data.setdefault("raw_path", pending["raw_path"])

    if should_write:
        actions_name = pending.get("actions_output")
        if not actions_name:
            actions_name = pending_path.name.replace("ingest-", "ingest-actions-", 1)
        actions_path = pending_path.parent / actions_name
        actions_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Wrote actions to %s", workspace_relpath(actions_path))

    return data
