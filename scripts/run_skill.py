"""Thin harness: load skill + pending context, call LLM once per skill unit."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from config import WORKSPACE_PATH
from llm_provider import call_llm, extract_json_object, provider_name

logger = logging.getLogger(__name__)

TEXT_KINDS = frozenset({"query", "lint"})


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
        prefix = "query-answer-" if kind == "query" else "lint-output-"
        out_name = pending_path.name.replace(f"{kind}-", prefix, 1).replace(".json", ".md")
    out_path = Path(out_name)
    if not out_path.is_absolute():
        out_path = WORKSPACE_PATH / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response_text, encoding="utf-8")
    logger.info("Wrote %s output to %s", pending.get("kind"), out_path.relative_to(WORKSPACE_PATH))
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
    skill_rel = pending.get("skill", "skills/ingest.md")
    skill_path = WORKSPACE_PATH / skill_rel
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")

    _, system_instruction = parse_skill(skill_path)
    user_message = pending.get("user_message")
    if not user_message:
        raise ValueError(f"pending file missing user_message: {pending_path}")

    subject = pending.get("raw_path") or pending.get("query") or pending_path.name
    logger.info(
        "Running skill %s (%s) via %s for %s",
        skill_rel,
        kind,
        provider_name(provider),
        subject,
    )

    response_text = call_llm(user_message, system_instruction, provider=provider)
    if not response_text:
        raise RuntimeError("LLM returned empty response")

    should_write = write_output if write_output is not None else write_actions

    if kind in TEXT_KINDS:
        out_path = None
        if should_write:
            out_path = _write_text_output(pending, pending_path, response_text)
        return {
            "text": response_text,
            "kind": kind,
            "output_path": str(out_path.relative_to(WORKSPACE_PATH)) if out_path else None,
        }

    if kind != "ingest":
        raise ValueError(f"Unknown skill kind: {kind}")

    data = extract_json_object(response_text)
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
        logger.info("Wrote actions to %s", actions_path.relative_to(WORKSPACE_PATH))

    return data
