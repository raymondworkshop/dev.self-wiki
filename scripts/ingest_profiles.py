"""Resolve ingest profile from raw path."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

from config import SKILLS_DIR, WORKSPACE_PATH

_PROFILES_PATH = SKILLS_DIR / "ingest-profiles.yaml"
_CACHE: dict | None = None


def _load_profiles() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not _PROFILES_PATH.exists():
        _CACHE = {"profiles": {}}
        return _CACHE
    data = yaml.safe_load(_PROFILES_PATH.read_text(encoding="utf-8")) or {}
    _CACHE = data
    return data


def resolve_profile(rel_path: str) -> dict | None:
    """Return profile dict for a path like raw/_posts/foo.md or _posts/foo.md."""
    norm = rel_path.replace("\\", "/")
    if not norm.startswith("raw/"):
        norm = f"raw/{norm}"

    profiles = _load_profiles().get("profiles", {})
    for _name, profile in profiles.items():
        pattern = profile.get("match", "")
        if fnmatch.fnmatch(norm, pattern):
            return {**profile, "name": _name}
    return None


def is_compressible(rel_path: str) -> bool:
    profile = resolve_profile(rel_path)
    return profile is not None and profile.get("mode") in ("summarize", "distill-lite")
