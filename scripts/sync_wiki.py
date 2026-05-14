import os
import re
import requests
import logging
from pathlib import Path
from datetime import datetime

# Configure logging for observability
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def sync_wiki():
    # Resolve workspace relative to script location for portability
    workspace = Path(__file__).parent.parent.resolve()
    raw_dir = workspace / "raw"
    wiki_dir = workspace / "wiki"
    config_file = workspace / "GEMINI.md"
    
    if not config_file.exists():
        logger.error(f"Configuration file {config_file} not found.")
        return
    
    # 1. Prepare the Context
    with open(config_file, "r") as f:
        instructions = f.read()
    
    # Gather recent raw files (last week or all)
    # For a full sync, we provide the directory structure
    # pathlib.Path.rglob() follows symbolic links by default,
    # so files within a softlinked directory (e.g., 'raw/_posts' pointing to another directory)
    # will be included in the processing.
    raw_content = ""
    for path in raw_dir.rglob("*.md"):
        try:
            raw_content += f"\n--- FILE: {path.relative_to(workspace)} ---\n"
            raw_content += path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Could not read {path}: {e}")

    # 2. Construct the Prompt
    prompt = f"""
    {instructions}
    
    ACTUAL DATA FROM RAW/:
    {raw_content}
    
    COMMAND: update wiki/ based on raw/ and GEMINI.md
    
    Please output the content for each wiki page that needs to be created or updated. 
    Format your response as a series of code blocks, each starting with the relative path of the file.
    """

    # 3. Call the LLM (Using Ollama endpoint from AGENTS.md)
    # Note: Replace with Gemini API if preferred
    ollama_url = os.environ.get("OLLAMA_URL", "http://100.90.225.26:11434/api/generate")
    payload = {
        "model": os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q5_K_M"),
        "prompt": prompt,
        "stream": False
    }

    logger.info("Requesting wiki update from LLM...")
    response = requests.post(ollama_url, json=payload)
    
    if response.status_code == 200:
        raw_result = response.json().get("response", "")
        (workspace / "outputs/sync_log.md").write_text(raw_result)
        
        # 4. Parse 'result' and write files
        # Expected format: 
        # wiki/topic.md
        # ```markdown
        # content
        # ```
        file_pattern = re.compile(r"(wiki/[a-zA-Z0-9_\-/]+\.md)\s+```(?:markdown)?\n(.*?)\n```", re.DOTALL)
        matches = file_pattern.findall(raw_result)
        
        for file_path_str, content in matches:
            target_path = workspace / file_path_str
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content.strip(), encoding='utf-8')
            logger.info(f"Updated: {file_path_str}")

        # 5. Update INDEX.md alphabetically
        update_index(wiki_dir)
        logger.info("Sync completed and INDEX.md updated.")
    else:
        logger.error(f"LLM request failed: {response.status_code} - {response.text}")

def update_index(wiki_dir):
    index_path = wiki_dir / "INDEX.md"
    # Get all .md files except INDEX and audit
    topics = []
    for f in wiki_dir.glob("*.md"):
        if f.name not in ["INDEX.md", "audit.md"]:
            topics.append(f.stem)
    
    topics.sort(key=str.lower)
    
    with open(index_path, "w", encoding='utf-8') as f:
        f.write("# Wiki Index\n\n")
        for topic in topics:
            f.write(f"* [[{topic}]]\n")

if __name__ == "__main__":
    sync_wiki()
