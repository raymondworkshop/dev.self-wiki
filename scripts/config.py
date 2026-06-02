import os
from pathlib import Path


# Load environment variables
def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env(Path(__file__).parent.parent / ".env")

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
GEMINI_CONF = WORKSPACE_PATH / "GEMINI.md"
LOG_MD = LOG_DIR / "log.md"
INDEX_MD = LOG_DIR / "index.md"
INDEX_JSON = LOG_DIR / "INDEX.json"
AUDIT_MD = WORKSPACE_PATH / "self-wiki" / "audit.md"
TWIN_PROFILE = WORKSPACE_PATH / "twin" / "PROFILE.md"
TWIN_DIR = TWIN_PROFILE.parent

# Ensure directories exist
for d in [RAW_DIR, WIKI_DIR, OUTPUTS_DIR, LOG_DIR, PENDING_DIR, SKILLS_DIR, TWIN_DIR]:
    d.mkdir(parents=True, exist_ok=True)
