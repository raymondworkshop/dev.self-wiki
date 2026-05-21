import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.resolve()))

import hashlib
import json
import logging
import os
import re
from datetime import datetime

import requests
import yaml
from config import GEMINI_CONF, LOG_DIR, RAW_DIR, WIKI_DIR, load_env
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
    Calls the LLM using the local MLX server.
    """
    # Force reload env vars to ensure we have the latest configuration
    load_env(Path(__file__).parent.parent / ".env")

    url = os.environ.get("LLM_URL", "http://100.90.225.26:8080/v1/chat/completions")
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
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"MLX call failed at {url}: {e}")
        return None


def chunk_text(text: str, max_lines: int = 500):
    """Splits text into chunks of roughly max_lines."""
    lines = text.splitlines()
    for i in range(0, len(lines), max_lines):
        yield "\n".join(lines[i : i + max_lines])


def distill_content(
    rel_path: str, content: str, is_chunk: bool = False, abs_path: Path = None
):
    """
    Core distillation logic for a piece of content.
    """
    instructions = GEMINI_CONF.read_text(encoding="utf-8")

    # Get existing wiki titles and aliases for semantic matching
    existing_titles = []
    for f in WIKI_DIR.glob("*.md"):
        try:
            p = WikiPage(f)
            if p.front_matter.get("title"):
                existing_titles.append(p.front_matter["title"])
            if p.front_matter.get("alias"):
                existing_titles.append(p.front_matter["alias"])
        except:
            continue

    titles_context = "\n".join([f"- {t}" for t in sorted(list(set(existing_titles)))])
    chunk_context = " (This is a chunk of a larger file)" if is_chunk else ""

    # Socratic Mirror Prompt
    prompt = f"""
You are a knowledge synthesizer.
LANGUAGE RULE: ALWAYS respond in the EXACT same language as the "ACTUAL DATA". NO translation is allowed.

I am providing content from a raw source: [[{rel_path}]]{chunk_context}
Content:
---
{content}
---

Existing Themes in the Wiki:
{titles_context}

Your task is to distill this into the Self-Wiki following the "Socratic Mirror" principles.
1. **Semantic Matching**: Review the 'Existing Themes'. If this content relates to one of them, choose that exact existing title. If creating a new title, it MUST be concise and professional. DO NOT use informal parenthetical suffixes like "(Initial Draft)", "(Draft)", or "(Notes)".
2. **Bilingual Alias**: Provide an alias in the OTHER language (if source is Chinese, provide English; if source is English, provide Chinese). If content is neutral, leave empty.
3. **Diarization**: Extract semantic "nuggets" or insights.
4. **Fidelity**: Use EXACTLY ONE single blockquote character ("> ") for the summary. Do NOT use double quotes or nested blockquotes ("> >").
5. **Tagging**: Generate relevant tags. Include at least one functional tag from the taxonomy:
   - `type/synthesis`: For connecting dots across entries.
   - `type/principle`: For fundamental life laws or mental models.
   - `type/shift`: For significant changes in belief or behavior.
   - Add your own semantic tags for topical categorization.
6. **Level**: Assign a level (1: Synthesis, 2: Principle).


Output your response as a JSON object:
{{
  "actions": [
    {{
      "target_title": "Choose from Existing Themes or Create New",
      "bilingual_alias": "Translation or Alias in other language",
      "level": 1,
      "summary": "2-3 sentence Socratic summary",
      "description": "A concise description of this page.",
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

            # Store the bilingual alias if provided
            if action.get("bilingual_alias"):
                page.front_matter["alias"] = action["bilingual_alias"]

            if not page.summary:
                # Ensure summary is clean of any '>' characters before saving
                summary = action["summary"].strip()
                # Remove any number of leading '>' characters followed by optional space
                summary = re.sub(r"^(>\s*)+", "", summary)
                page.summary = summary

            # Update description if it's missing or empty
            if not page.front_matter.get("description"):
                page.front_matter["description"] = action.get("description", "")

            # Smart Merging: Check if content already exists to avoid duplicates
            # Strip leading blockquote markers from lines in LLM output
            cleaned_body = "\n".join(
                [
                    re.sub(r"^>\s*", "", line)
                    for line in action["new_body_content"].splitlines()
                ]
            )
            if cleaned_body.strip() not in page.body:
                # Add distillation section with source link
                page.body += f"\n\n### Distillation ({datetime.now().strftime('%Y-%m-%d')}) - source: [[../raw/{rel_path}]]\n{cleaned_body}\n"

            # Additive Traceability: Append the raw file path to the sources list
            # We use ../raw/ to point from self-wiki/wiki/ to self-wiki/raw/
            source_link = f"../raw/{rel_path}"
            if source_link not in page.sources:
                page.sources.append(source_link)

            # Log the source being added for transparency
            logger.info(f"Source linked: [[{rel_path}]] -> {action['target_title']}")

            current_tags = set(page.front_matter.get("tags", []))
            current_tags.update(action.get("tags", []))
            page.front_matter["tags"] = list(current_tags)
            page.save()
            logger.info(f"Integrated theme: {action['target_title']}")
            if abs_path:
                update_raw_with_link(abs_path, action["target_title"])
        return True
    except Exception as e:
        logger.error(f"Error processing actions for {rel_path}: {e}")
        return False


def update_raw_with_link(abs_p: Path, target_title: str):
    """Appends an 'Evolved into' link to the raw file."""
    try:
        content = abs_p.read_text(encoding="utf-8")
        link = f"\n\n---\nEvolved into: [[{target_title}]]"
        if f"[[{target_title}]]" not in content:
            abs_p.write_text(content + link, encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to update raw file {abs_p}: {e}")


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
        # Pass the abs_path to distill_content so it can update the raw file
        # We need to adjust distill_content to accept this
        return distill_content(rel_path, raw_content, abs_path=abs_path)


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
            # Recalculate hash after distillation in case update_raw_with_link modified it
            new_hash = hashlib.md5(abs_p.read_bytes()).hexdigest()
            orchestrator.cache[rel] = new_hash
            orchestrator.save_cache()
        else:
            logger.warning(f"Skipping cache update for {rel} due to failure.")


if __name__ == "__main__":
    sync_wiki()
