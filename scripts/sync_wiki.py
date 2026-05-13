import os
import requests
from pathlib import Path

def sync_wiki():
    workspace = Path("/Users/zhaowenlong/workspace/dev.self-wiki")
    raw_dir = workspace / "raw"
    wiki_dir = workspace / "wiki"
    config_file = workspace / "GEMINI.md"
    
    # 1. Prepare the Context
    with open(config_file, "r") as f:
        instructions = f.read()
    
    # Gather recent raw files (last 24h or all)
    # For a full sync, we provide the directory structure
    raw_content = ""
    for path in raw_dir.rglob("*.md"):
        raw_content += f"\n--- FILE: {path.relative_to(workspace)} ---\n"
        raw_content += path.read_text()

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
    ollama_url = "http://100.90.225.26:11434/api/generate"
    payload = {
        "model": "qwen2.5:7b-instruct-q5_K_M",
        "prompt": prompt,
        "stream": False
    }

    print("Sending sync request to LLM...")
    response = requests.post(ollama_url, json=payload)
    
    if response.status_code == 200:
        result = response.json().get("response", "")
        # 4. Logic to parse 'result' and write files to wiki_dir goes here.
        # For now, we log the result or write a summary.
        (workspace / "outputs/sync_log.md").write_text(result)
        print("Sync completed. See outputs/sync_log.md for details.")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    sync_wiki()
