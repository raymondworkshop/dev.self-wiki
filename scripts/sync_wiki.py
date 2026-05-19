import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import requests


# Configure logging
# Load .env first from project root to get WORKSPACE_PATH
def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


# Assuming scripts are in /scripts/, so project root is one level up
load_env(Path(__file__).parent.parent / ".env")
workspace = Path(
    os.environ.get(
        "WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki/self-wiki"
    )
)

log_dir = workspace / "log"
log_dir.mkdir(parents=True, exist_ok=True)
execution_log = log_dir / "sync_execution.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.FileHandler(execution_log), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class SyncTracker:
    def __init__(self, cache_path):
        self.cache_path = Path(cache_path)
        self.cache = self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text())
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}

    def save_cache(self):
        self.cache_path.write_text(json.dumps(self.cache, indent=2))

    def get_file_hash(self, path):
        import hashlib

        hasher = hashlib.md5()
        with open(path, "rb") as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def is_changed(self, relative_path, absolute_path):
        current_hash = self.get_file_hash(absolute_path)
        old_hash = self.cache.get(str(relative_path))
        if current_hash != old_hash or old_hash == "FORCE_RESYNC":
            self.cache[str(relative_path)] = current_hash
            return True
        return False


def sync_wiki():
    raw_dir = workspace / "raw"
    wiki_dir = workspace  # root of self-wiki
    config_file = workspace.parent / "GEMINI.md"
    cache_file = workspace / "log" / ".sync_cache.json"

    with open(config_file, "r") as f:
        instructions = f.read()

    tracker = SyncTracker(cache_file)
    changed_files = []

    for root, dirs, files in os.walk(raw_dir):
        for file in files:
            if file.endswith(".md"):
                path = Path(root) / file
                rel_path = path.relative_to(workspace.parent)
                if tracker.is_changed(rel_path, path):
                    changed_files.append((rel_path, path))

    if not changed_files:
        logger.info("No new or modified files to sync.")
        return

    logger.info(f"Found {len(changed_files)} changed files. Adaptive processing...")

    # Process files
    for rel, abs_path in changed_files:
        logger.info(f"Syncing: {rel}")
        if process_batch([(rel, abs_path)], instructions, workspace, wiki_dir):
            tracker.save_cache()
        else:
            logger.error(f"Failed to sync {rel}. Cache not updated.")

    update_index(wiki_dir)


def call_llm_for_batch(raw_content, instructions, workspace, wiki_dir):
    # Context-aware logic
    target_wiki_pages = set()
    for wiki_file in wiki_dir.rglob("*.md"):
        if wiki_file.stem.lower() in raw_content.lower():
            target_wiki_pages.add(wiki_file)

    existing_context = ""
    for wiki_path in target_wiki_pages:
        if (
            wiki_path.exists()
            and wiki_path.name not in ["INDEX.md", "audit.md"]
            and not wiki_path.name.endswith("-Hub.md")
        ):
            existing_context += f"\n--- EXISTING WIKI: {wiki_path.name} ---\n"
            existing_context += wiki_path.read_text(encoding="utf-8")

    prompt = f"""
You are the "Second Brain" for a developer/thinker.
Synthesize notes into the wiki.
{instructions}
EXISTING WIKI: {existing_context}
ACTUAL DATA: {raw_content}
"""

    # Use environment variables for LLM configuration
    llm_provider = os.environ.get("LLM_PROVIDER", "mlx").lower()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    if llm_provider == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
        model = os.environ.get("LLM_MODEL", "deepseek-chat")
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        url = os.environ.get("LLM_URL", "http://100.90.225.26:8080/v1/chat/completions")
        model = os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit")
        headers = {}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "stream": False,
    }

    try:
        logger.info(f"Using {llm_provider.upper()} for batch processing...")
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        if response.status_code == 200:
            # ... (parsing logic remains the same)
            raw_result = (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            blocks = re.findall(r"```(?:markdown)?\n(.*?)\n```", raw_result, re.DOTALL)
            for block in blocks:
                lines = block.splitlines()
                if not lines:
                    continue
                first_line = lines[0].strip()
                if first_line.startswith("wiki/") and first_line.endswith(".md"):
                    target_path = workspace / first_line
                    content = "\n".join(lines[1:]).strip()
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content, encoding="utf-8")
            return True
        else:
            logger.error(
                f"LLM request failed: {response.status_code} - {response.text}"
            )
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            return False
    except Exception as e:
        logger.error(f"Sync error: {e}")
        logger.error(f"URL: {url}")
        return False


def process_batch(batch, instructions, workspace, wiki_dir):
    rel_path, abs_path = batch[0]
    lines = abs_path.read_text(encoding="utf-8").splitlines()
    if len(lines) > 800:
        chunk_size = 400
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i : i + chunk_size]
            chunk_content = (
                f"\n--- FILE: {rel_path} (Chunk {i // chunk_size + 1}) ---\n"
                + "\n".join(chunk_lines)
            )
            if not call_llm_for_batch(chunk_content, instructions, workspace, wiki_dir):
                return False
        return True

    return call_llm_for_batch(
        abs_path.read_text(encoding="utf-8"), instructions, workspace, wiki_dir
    )


def update_index(wiki_dir):
    index_path = wiki_dir / "INDEX.md"
    topics = sorted(
        [
            f.stem
            for f in wiki_dir.rglob("*.md")
            if f.name not in ["INDEX.md", "audit.md"] and not f.name.endswith("-Hub.md")
        ],
        key=str.lower,
    )
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# Wiki Index\n\n")
        for topic in topics:
            f.write(f"* [[{topic}]]\n")


if __name__ == "__main__":
    sync_wiki()
