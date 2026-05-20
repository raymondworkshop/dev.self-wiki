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
    os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
)


log_dir = workspace / "self-wiki" / "log"
log_dir.mkdir(parents=True, exist_ok=True)
execution_log = log_dir / "sync_execution.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.FileHandler(execution_log), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
logger.info(f"Using workspace path: {workspace}")


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
        return current_hash != old_hash or old_hash == "FORCE_RESYNC"

    def update_hash(self, relative_path, absolute_path):
        current_hash = self.get_file_hash(absolute_path)
        self.cache[str(relative_path)] = current_hash


def sync_wiki():
    self_wiki_dir = workspace / "self-wiki"
    raw_dir = self_wiki_dir / "raw"
    wiki_dir = self_wiki_dir / "wiki"  # self-wiki
    config_file = workspace / "GEMINI.md"
    cache_file = self_wiki_dir / "log" / ".sync_cache.json"

    with open(config_file, "r") as f:
        instructions = f.read()

    tracker = SyncTracker(cache_file)
    changed_files = []

    for root, dirs, files in os.walk(raw_dir):
        for file in files:
            if file.endswith(".md"):
                path = Path(root) / file
                rel_path = path.relative_to(self_wiki_dir.parent)
                if tracker.is_changed(rel_path, path):
                    changed_files.append((rel_path, path))

    if not changed_files:
        logger.info("No new or modified files to sync.")
        return

    logger.info(f"Found {len(changed_files)} changed files. Adaptive processing...")

    # Process files
    for rel, abs_path in changed_files:
        logger.info(f"Syncing: {rel}")
        if process_batch([(rel, abs_path)], instructions, self_wiki_dir, wiki_dir):
            tracker.update_hash(rel, abs_path)
            tracker.save_cache()
        else:
            logger.error(f"Failed to sync {rel}. Cache not updated.")

    update_index(wiki_dir)


def call_llm_for_batch(raw_content, source_path, instructions, self_wiki_dir, wiki_dir):
    # Context-aware logic: Provide all potential wiki pages to the LLM and let it choose the best one.
    all_wiki_pages = [
        f.name
        for f in wiki_dir.rglob("*.md")
        if f.name not in ["INDEX.md", "audit.md"] and not f.name.endswith("-Hub.md")
    ]
    context_list = "\n".join([f"- {name}" for name in all_wiki_pages])

    prompt = f"""
    You are a Second Brain knowledge synthesizer.
    {instructions}
    SOURCE FILE: {source_path}
    LANGUAGE RULE: ALWAYS respond in the EXACT same language as the "ACTUAL DATA". NO translation is allowed.

    AVAILABLE WIKI PAGES:
    {context_list}

    ACTUAL DATA: {raw_content}

    INSTRUCTIONS:
    1. Determine ALL relevant wiki pages to merge into. If none fit, create a new file where filename is the title slugified (e.g., `wiki/Title_of_Page.md`).
    2. Output markdown code blocks for EACH relevant page.
    3. Strict Output Format (Example):
    ```markdown
    wiki/Knowledge_Title.md
    ---
    last_updated: 2026-05-19T10:00:00Z
    title: Knowledge Title
    description: A concise description.
    tags: [type/synthesis, work, self]
    ---

    > A 2-3 sentence summary here.

    ## Evolution
    - Initial insights about the topic.

    ## Content
    ...content merged with ACTUAL DATA...

    ## Backlinks
    <!-- BEGIN BACKLINKS -->
    - **Evolved from**: [[Topic]]
    - **Mentioned in**: [[Topic]]
    - **Contradicts**: [[Topic]]
    <!-- END BACKLINKS -->

    ## Sources
    - [[{source_path}]] (Append this to the existing list of sources)
    ```
    4. DO NOT include any text outside the code blocks.
    """  # Use environment variables for LLM configuration

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
        # logger.info(f"Sending request to {url}...")
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        if response.status_code == 200:
            # ... (parsing logic remains the same)
            raw_result = (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            # logger.info(f"LLM RESPONSE: {raw_result}")
            blocks = re.findall(r"```(?:markdown)?\n(.*?)\n```", raw_result, re.DOTALL)
            for block in blocks:
                lines = block.splitlines()
                if not lines:
                    continue
                first_line = lines[0].strip()
                if first_line.startswith("wiki/") and first_line.endswith(".md"):
                    target_path = self_wiki_dir / first_line
                    content = "\n".join(lines[1:]).strip()
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content, encoding="utf-8")
            return True
        else:
            logger.error(
                f"LLM request failed: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=True)
        return False


def process_batch(batch, instructions, self_wiki_dir, wiki_dir):
    rel_path, abs_path = batch[0]
    content = abs_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    if len(lines) > 500:
        logger.info(f"File {rel_path} is large ({len(lines)} lines). Chunking...")
        chunk_size = 500
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i : i + chunk_size]
            chunk_content = (
                f"\n--- FILE: {rel_path} (Chunk {i // chunk_size + 1}) ---\n"
                + "\n".join(chunk_lines)
            )
            if not call_llm_for_batch(
                chunk_content, str(rel_path), instructions, self_wiki_dir, wiki_dir
            ):
                return False
        return True

    return call_llm_for_batch(
        content, str(rel_path), instructions, self_wiki_dir, wiki_dir
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
