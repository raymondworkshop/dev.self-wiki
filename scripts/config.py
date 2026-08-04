import os
from pathlib import Path


_DEFAULT_ENV = Path(__file__).parent.parent / ".env"


def _parse_env_value(raw: str) -> str:
    value = raw.strip().strip('"').strip("'")
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    return value


def load_env(env_path: Path | None = None) -> None:
    path = env_path or _DEFAULT_ENV
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), _parse_env_value(value))


load_env()

WORKSPACE_PATH = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)
# Vault (often iCloud symlink) — human notes only; avoid writing runtime state here.
VAULT_DIR = WORKSPACE_PATH / "self-wiki"
RAW_DIR = VAULT_DIR / "raw"
WIKI_DIR = VAULT_DIR / "wiki"
OUTPUTS_DIR = VAULT_DIR / "outputs"
# Repo-local (outside iCloud) — logs, indexes, twin snapshot for launchd/scripts
LOG_DIR = WORKSPACE_PATH / "log"
PENDING_DIR = LOG_DIR / "pending"
LAUNCHD_DIR = WORKSPACE_PATH / "launchd"
SKILLS_DIR = WORKSPACE_PATH / "skills"
QUERY_SKILL = SKILLS_DIR / "query.md"
RBRAIN_SKILL = SKILLS_DIR / "rbrain.md"
LINT_SKILL = SKILLS_DIR / "lint.md"
QUERY_PROFILES = SKILLS_DIR / "query-profiles.yaml"
RBRAIN_INDEX_JSON = LOG_DIR / "rbrain-index.json"
RBRAIN_OUTPUTS_DIR = OUTPUTS_DIR / "rbrain"


def _resolve_operating_manual() -> Path:
    for name in ("AGENTS.md", "GEMINI.md"):
        path = WORKSPACE_PATH / name
        if path.exists():
            return path
    raise FileNotFoundError(
        f"No operating manual found (expected AGENTS.md or GEMINI.md in {WORKSPACE_PATH})"
    )


GEMINI_CONF = _resolve_operating_manual()
LOG_MD = LOG_DIR / "log.md"
MEMEX_DIR = LOG_DIR / "memex"
INDEX_MD = LOG_DIR / "index.md"
INDEX_JSON = LOG_DIR / "INDEX.json"
AUDIT_MD = VAULT_DIR / "audit.md"
TWIN_PROFILE = WORKSPACE_PATH / "twin" / "PROFILE.md"
TWIN_PRINCIPLES_JSON = WORKSPACE_PATH / "twin" / "principles.json"
TWIN_DIR = TWIN_PROFILE.parent


def workspace_relpath(path: Path) -> str:
    """Path relative to WORKSPACE_PATH (works when self-wiki is an iCloud symlink)."""
    p = Path(path)
    try:
        return str(p.relative_to(WORKSPACE_PATH)).replace("\\", "/")
    except ValueError:
        pass
    vault = VAULT_DIR.resolve()
    resolved = p.resolve()
    if resolved == vault or vault in resolved.parents:
        suffix = resolved.relative_to(vault)
        return f"self-wiki/{suffix}".replace("\\", "/")
    return str(resolved.relative_to(WORKSPACE_PATH.resolve())).replace("\\", "/")


def twin_profile_max_principles() -> int:
    return max(1, int(os.environ.get("TWIN_PROFILE_MAX_PRINCIPLES", "80")))


def twin_query_principles_k() -> int:
    return max(1, int(os.environ.get("TWIN_QUERY_PRINCIPLES_K", "25")))


def twin_profile_excerpt_chars() -> int:
    return max(500, int(os.environ.get("TWIN_PROFILE_EXCERPT_CHARS", "3000")))


def twin_profile_max_evolution() -> int:
    return max(1, int(os.environ.get("TWIN_PROFILE_MAX_EVOLUTION", "15")))


def ensure_workspace_dirs() -> None:
    """Create local runtime dirs; vault dirs only if writable (skip under launchd/iCloud blocks)."""
    for d in [LOG_DIR, PENDING_DIR, LAUNCHD_DIR, SKILLS_DIR, TWIN_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    for d in [RAW_DIR, WIKI_DIR, OUTPUTS_DIR]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


ensure_workspace_dirs()
