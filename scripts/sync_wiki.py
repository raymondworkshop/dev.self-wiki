import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import requests
import yaml
from config import GEMINI_CONF, LOG_DIR, RAW_DIR, WIKI_DIR
from models import WikiPage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "sync_v2.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def call_llm(prompt: str, system_instruction: str = ""):
    """
    Calls the LLM based on LLM_PROVIDER in .env.
    Supports Gemini and OpenAI-compatible (MLX, DeepSeek, etc.)
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not found.")
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {"parts": [{"text": f"{system_instruction}\n\nUser Query: {prompt}"}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "maxOutputTokens": 4096,
            },
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return None

    else:
        # OpenAI-compatible (MLX, DeepSeek, Ollama)
        url = os.environ.get("LLM_URL")
        api_key = (
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("DEEPSEEK_API_KEY")
            or "no-key"
        )
        model = os.environ.get("LLM_MODEL", "mlx-model")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"{provider.upper()} call failed at {url}: {e}")
            return None


def chunk_text(text: str, max_lines: int = 500):
    """Splits text into chunks of roughly max_lines."""
    lines = text.splitlines()
    for i in range(0, len(lines), max_lines):
        yield "\n".join(lines[i : i + max_lines])


def distill_content(rel_path: str, content: str, is_chunk: bool = False):
    """
    Core distillation logic for a piece of content.
    """
    instructions = GEMINI_CONF.read_text(encoding="utf-8")

    # Get existing wiki titles for semantic matching
    existing_titles = []
    for f in WIKI_DIR.glob("*.md"):
        try:
            p = WikiPage(f)
            if p.front_matter.get("title"):
                existing_titles.append(p.front_matter["title"])
        except:
            continue

    titles_context = "\n".join([f"- {t}" for t in sorted(list(set(existing_titles)))])
    chunk_context = " (This is a chunk of a larger file)" if is_chunk else ""

    # Socratic Mirror Prompt
    prompt = f"""
I am providing content from a raw source: [[{rel_path}]]{chunk_context}
Content:
---
{content}
---

Existing Themes in the Wiki:
{titles_context}

Your task is to distill this into the Self-Wiki following the "Socratic Mirror" principles.
1. **Semantic Matching**: Review the 'Existing Themes'. If this content relates to one of them (even if the wording differs), choose that exact existing title. Only create a new title if the topic is substantially different.
2. **Diarization**: Extract semantic "nuggets" or insights.
3. **Fidelity**: Use direct blockquotes ("> ") for raw truth. Do NOT interpret unless necessary.
4. **Tagging**: Generate relevant tags. Include at least one functional tag from the taxonomy:
   - `type/synthesis`: For connecting dots across entries.
   - `type/principle`: For fundamental life laws or mental models.
   - `type/shift`: For significant changes in belief or behavior.
   - Add your own semantic tags for topical categorization.
5. **Level**: Assign a level (1: Synthesis, 2: Principle).

Output your response as a JSON object:
{{
  "actions": [
    {{
      "target_title": "Choose from Existing Themes or Create New",
      "level": 1,
      "summary": "2-3 sentence Socratic summary",
      "new_body_content": "The distilled insights, integrated with existing knowledge if possible",
      "tags": ["type/synthesis", "topic/growth", "emotion/anxiety"]
    }}
  ]
}}
"""

    response_text = call_llm(prompt, instructions)
    if not response_text:
        return False

    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not json_match:
        logger.error(f"Invalid JSON response for {rel_path}")
        return False

    try:
        data = json.loads(json_match.group(0))
        for action in data.get("actions", []):
            page = WikiPage.create_new(action["target_title"], level=action["level"])

            if not page.summary:
                page.summary = action["summary"]

            # Smart Merging: Check if content already exists to avoid duplicates
            if action["new_body_content"].strip() not in page.body:
                page.body += f"\n\n### Distillation ({datetime.now().strftime('%Y-%m-%d')})\n{action['new_body_content']}\n"

            # Additive Traceability: Append the raw file path to the sources list
            if rel_path not in page.sources:
                page.sources.append(rel_path)

            # Log the source being added for transparency
            logger.info(f"Source linked: [[{rel_path}]] -> {action['target_title']}")

            current_tags = set(page.front_matter.get("tags", []))
            current_tags.update(action.get("tags", []))
            page.front_matter["tags"] = list(current_tags)
            page.save()
            logger.info(f"Integrated theme: {action['target_title']}")
        return True
    except Exception as e:
        logger.error(f"Error processing actions for {rel_path}: {e}")
        return False


def distill_file(rel_path: str, abs_path: Path):
    """
    Processes a single raw file, handles chunking if necessary.
    """
    raw_content = abs_path.read_text(encoding="utf-8")
    line_count = len(raw_content.splitlines())

    if line_count > 500:
        logger.info(f"Large file detected ({line_count} lines). Chunking...")
        success = True
        for i, chunk in enumerate(chunk_text(raw_content, 500)):
            logger.info(f"Processing chunk {i + 1} of {rel_path}")
            if not distill_content(rel_path, chunk, is_chunk=True):
                success = False
        return success
    else:
        return distill_content(rel_path, raw_content)


def sync_wiki():
    """Main sync loop."""
    from orchestrator import SocraticOrchestrator

    orchestrator = SocraticOrchestrator()
    changed = orchestrator.get_changed_files()

    if not changed:
        logger.info("Nothing to sync.")
        return

    logger.info(f"Starting distillation for {len(changed)} files.")

    for rel, abs_p, h in changed:
        if distill_file(rel, abs_p):
            orchestrator.cache[rel] = h
            orchestrator.save_cache()
        else:
            logger.warning(f"Skipping cache update for {rel} due to failure.")

    if __name__ == "__main__":

    sync_wiki()
