"""Skill registry loader: decouple pipeline stages from concrete skill files."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from config import WORKSPACE_PATH


def _registry_path() -> Path:
    configured = os.environ.get("SKILL_REGISTRY_PATH", "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = WORKSPACE_PATH / path
        return path
    return WORKSPACE_PATH / "skills" / "skill-registry.yaml"


def _load_registry() -> dict:
    path = _registry_path()
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def resolve_skill(
    role: str,
    default_skill: str,
    *,
    raw_rel: str | None = None,
    current_skill: str | None = None,
) -> str:
    """Resolve skill path for role with optional raw-prefix/current-skill routing."""

    registry = _load_registry()
    section = registry.get(role)
    if isinstance(section, str) and section.strip():
        return section.strip()
    if not isinstance(section, dict):
        return default_skill

    by_raw_prefix = section.get("by_raw_prefix")
    if isinstance(by_raw_prefix, dict) and raw_rel:
        rel = raw_rel[4:] if raw_rel.startswith("raw/") else raw_rel
        best_match = ""
        selected = None
        for prefix, skill in by_raw_prefix.items():
            if not isinstance(prefix, str) or not isinstance(skill, str):
                continue
            if rel.startswith(prefix) and len(prefix) > len(best_match):
                best_match = prefix
                selected = skill
        if selected:
            return selected

    by_current_skill = section.get("by_current_skill")
    active = current_skill or default_skill
    if isinstance(by_current_skill, dict) and active:
        mapped = by_current_skill.get(active)
        if isinstance(mapped, str) and mapped.strip():
            return mapped.strip()

    default = section.get("default")
    if isinstance(default, str) and default.strip():
        return default.strip()
    return default_skill
