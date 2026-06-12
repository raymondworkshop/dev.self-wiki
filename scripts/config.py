import os
from pathlib import Path


_DEFAULT_ENV = Path(__file__).parent.parent / ".env"


def load_env(env_path: Path | None = None) -> None:
    path = env_path or _DEFAULT_ENV
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

WORKSPACE_PATH = Path(
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)
RAW_DIR = WORKSPACE_PATH / "self-wiki" / "raw"
WIKI_DIR = WORKSPACE_PATH / "self-wiki" / "wiki"
OUTPUTS_DIR = WORKSPACE_PATH / "self-wiki" / "outputs"
LOG_DIR = WORKSPACE_PATH / "self-wiki" / "log"
PENDING_DIR = LOG_DIR / "pending"
SKILLS_DIR = WORKSPACE_PATH / "skills"
INGEST_SKILL = SKILLS_DIR / "ingest.md"
QUERY_SKILL = SKILLS_DIR / "query.md"
LINT_SKILL = SKILLS_DIR / "lint.md"
QUERY_PROFILES = SKILLS_DIR / "query-profiles.yaml"
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
INDEX_MD = LOG_DIR / "index.md"
INDEX_JSON = LOG_DIR / "INDEX.json"
AUDIT_MD = WORKSPACE_PATH / "self-wiki" / "audit.md"
TWIN_PROFILE = WORKSPACE_PATH / "twin" / "PROFILE.md"
TWIN_PRINCIPLES_JSON = WORKSPACE_PATH / "twin" / "principles.json"
TWIN_DIR = TWIN_PROFILE.parent


def twin_profile_max_principles() -> int:
    return max(1, int(os.environ.get("TWIN_PROFILE_MAX_PRINCIPLES", "80")))


def twin_query_principles_k() -> int:
    return max(1, int(os.environ.get("TWIN_QUERY_PRINCIPLES_K", "25")))


def twin_profile_excerpt_chars() -> int:
    return max(500, int(os.environ.get("TWIN_PROFILE_EXCERPT_CHARS", "3000")))


def twin_profile_max_evolution() -> int:
    return max(1, int(os.environ.get("TWIN_PROFILE_MAX_EVOLUTION", "15")))

# Ensure directories exist
for d in [RAW_DIR, WIKI_DIR, OUTPUTS_DIR, LOG_DIR, PENDING_DIR, SKILLS_DIR, TWIN_DIR]:
    d.mkdir(parents=True, exist_ok=True)
