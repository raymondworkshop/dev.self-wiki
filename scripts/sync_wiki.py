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


def get_gemini_response(messages, instructions):
    """Call Google Gemini API via REST."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")

    if not api_key:
        logger.error("GEMINI_API_KEY not set.")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    system_instruction = {"parts": [{"text": instructions}]}
    contents = []

    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    # Ensure alternating roles for Gemini (user -> model -> user)
    if contents and contents[0]["role"] == "model":
        contents.pop(0)

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
        "system_instruction": system_instruction,
    }

    try:
        response = requests.post(url, json=payload, timeout=400)
        response.raise_for_status()
        data = response.json()
        if "candidates" not in data or not data["candidates"]:
            return None
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini API Error in sync: {e}")
        return None


def call_llm(prompt: str, system_instruction: str = ""):
    """
    Calls the LLM based on LLM_PROVIDER.
    """
    # Force reload env vars to ensure we have the latest configuration
    load_env(Path(__file__).parent.parent / ".env")
    provider = os.environ.get("LLM_PROVIDER", "mlx").lower()

    if provider == "gemini":
        return get_gemini_response(
            [{"role": "user", "content": prompt}], system_instruction
        )

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
        response = requests.post(url, json=payload, headers=headers, timeout=360)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"MLX call failed at {url}: {e}")
        return None


def chunk_text(text: str, max_lines: int = 500, overlap: int = 50):
    """Splits text into chunks with a specified overlap to maintain context."""
    lines = text.splitlines()
    if not lines:
        return

    start = 0
    while start < len(lines):
        end = start + max_lines
        chunk = "\n".join(lines[start:end])
        yield chunk

        if end >= len(lines):
            break
        # Slide forward by max_lines - overlap
        start += max_lines - overlap


def detect_language(text: str) -> str:
    """Detects if the content is primarily Chinese or English."""
    if re.search(r"[\u4e00-\u9fff]", text):
        return "Chinese"
    return "English"


def distill_content(rel_path: str, content: str, is_chunk: bool = False):
    """
    Core distillation logic for a piece of content.
    """
    instructions = GEMINI_CONF.read_text(encoding="utf-8")

    # Get existing wiki titles and aliases for semantic matching
    existing_titles = []
    title_to_path = {}
    for f in WIKI_DIR.rglob("*.md", recurse_symlinks=True):
        try:
            # Simple header parsing to avoid full WikiPage load if not needed
            f_content = f.read_text(encoding="utf-8")
            t_match = re.search(r"^title:\s*(.*)", f_content, re.MULTILINE)
            a_match = re.search(r"^alias:\s*(.*)", f_content, re.MULTILINE)

            if t_match:
                title = t_match.group(1).strip().strip("'\"")
                existing_titles.append(title)
                title_to_path[title] = f
            if a_match:
                alias = a_match.group(1).strip().strip("'\"")
                existing_titles.append(alias)
                title_to_path[alias] = f
        except:
            continue

    titles_context = "\n".join([f"- {t}" for t in sorted(list(set(existing_titles)))])
    chunk_context = " (This is a chunk of a larger file)" if is_chunk else ""
    source_lang = detect_language(content)
    target_lang = "English" if source_lang == "Chinese" else "Chinese"

    # Socratic Mirror Prompt
    prompt = f"""
You are a knowledge synthesizer.
STRICT LANGUAGE RULE:
- The source content is in {source_lang}.
- All generated content (summary, description, body, target_title) MUST be in {source_lang}.
- **Target Title & Alias Rule**:
    1. Review the 'Existing Themes' below.
    2. If this content relates to an existing theme (matched by title OR alias), you MUST choose that EXACT title.
    3. If creating a NEW title in {source_lang}, you MUST also provide a 'bilingual_alias' strictly in {target_lang}.

I am providing content from a raw source: [[{rel_path}]]{chunk_context}
Content:
---
{content}
---

Existing Themes in the Wiki:
{titles_context}

Your task is to distill this into the Self-Wiki following the "Socratic Mirror" principles.
1. **Semantic Matching**: prioritize matching existing themes or their aliases across languages.
2. **Confidence Scoring**: Assign a `confidence_score` (0.0 to 1.0) and a `confidence_rationale`:
   - 0.9-1.0 (Literal): Direct, clear statement in source.
   - 0.7-0.89 (Explicit Pattern): Strong pattern shown by multiple explicit actions.
   - 0.5-0.69 (Synthesized Inference): Logical inference from recurring themes. MUST label content with `[AI Synthesis]`.
   - < 0.5 (Speculative Observation): Weak evidence or subtle tone. MUST label content with `[Socratic Observation]`.
3. **Bilingual Alias**: Provide a high-quality translation of the title strictly in {target_lang}.
4. **Diarization**: Extract semantic "nuggets". Use EXACTLY ONE single blockquote character ("> ") for the summary.
5. **Tagging**: Include functional tags: `type/synthesis`, `type/principle`, `type/shift`.
6. **Level**: Assign a level (1: Synthesis, 2: Principle).


Output your response as a JSON object:
{{
  "actions": [
    {{
      "target_title": "Choose from Existing Themes or Create New",
      "confidence_score": 0.85,
      "confidence_rationale": "Explanation based on evidence",
      "bilingual_alias": "Translation in {target_lang}",
      "level": 1,
      "summary": "2-3 sentence Socratic summary",
      "description": "Concise description",
      "new_body_content": "Distilled insights. If confidence < 0.7, start with [AI Synthesis] or [Socratic Observation]",
      "tags": ["type/synthesis", "topic/growth"]
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
            target_title = action["target_title"]

            # Check if this title or alias already exists in any directory
            if target_title in title_to_path:
                page = WikiPage(title_to_path[target_title])
                logger.info(
                    f"Merging into existing page: {title_to_path[target_title].name}"
                )
            else:
                page = WikiPage.create_new(target_title, level=action["level"])
                logger.info(f"Creating new page for theme: {target_title}")

            # Update confidence metrics
            page.front_matter["confidence"] = action.get("confidence_score", 1.0)
            page.front_matter["confidence_rationale"] = action.get(
                "confidence_rationale", ""
            )

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
            cleaned_body = "\n".join(
                [
                    re.sub(r"^>\s*", "", line)
                    for line in action["new_body_content"].splitlines()
                ]
            )
            if cleaned_body.strip() not in page.body:
                # Add distillation section with source link
                page.body += f"\n\n### Distillation ({datetime.now().strftime('%Y-%m-%d')}) - source: [[../raw/{rel_path}]]\n{cleaned_body}\n"

            # Additive Traceability
            source_link = f"../raw/{rel_path}"
            if source_link not in page.sources:
                page.sources.append(source_link)

            # Record Evolution
            evo_entry = f"- {datetime.now().strftime('%Y-%m-%d')}: Distilled from raw source [[{source_link}]]."
            if evo_entry not in page.evolution:
                page.evolution = (page.evolution + "\n" + evo_entry).strip()

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
    Adjusts chunking strategy based on LLM_PROVIDER.
    """
    raw_content = abs_path.read_text(encoding="utf-8")
    line_count = len(raw_content.splitlines())

    # Reload env to check provider
    load_env(Path(__file__).parent.parent / ".env")
    provider = os.environ.get("LLM_PROVIDER", "mlx").lower()

    # Adjust limits based on provider power
    if provider == "gemini":
        threshold = 8000
        chunk_size = 10000
        overlap = 500
    else:
        threshold = 220
        chunk_size = 500
        overlap = 50

    if line_count > threshold:
        logger.info(
            f"Large file detected ({line_count} lines). Chunking with overlap using {provider} limits..."
        )
        success = True
        for i, chunk in enumerate(chunk_text(raw_content, chunk_size, overlap)):
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
            new_hash = hashlib.md5(abs_p.read_bytes()).hexdigest()
            orchestrator.cache[rel] = new_hash
            orchestrator.save_cache()
        else:
            logger.warning(f"Skipping cache update for {rel} due to failure.")


if __name__ == "__main__":
    sync_wiki()
