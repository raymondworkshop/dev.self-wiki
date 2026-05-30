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
GEMINI_CONF = WORKSPACE_PATH / "GEMINI.md"

# Ensure directories exist
for d in [RAW_DIR, WIKI_DIR, OUTPUTS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)
