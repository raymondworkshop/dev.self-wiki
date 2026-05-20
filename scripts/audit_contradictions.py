import logging
import os
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


# Load .env
load_env(Path(__file__).parent.parent / ".env")


def audit_contradictions():
    workspace = Path(
        os.environ.get("WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki")
    )
    self_wiki_dir = workspace / "self-wiki"
    wiki_dir = self_wiki_dir / "wiki"
    wiki_files = list(wiki_dir.rglob("*.md"))

    # Analyze files in batches for contradictions
    batch_size = 5
    llm_provider = os.environ.get("LLM_PROVIDER", "mlx").lower()
    llm_model = os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit")

    logger.info("Auditing wiki for cognitive contradictions...")

    for i in range(0, len(wiki_files), batch_size):
        batch = wiki_files[i : i + batch_size]
        batch_content = "\n".join(
            [f"--- FILE: {f.name} ---\n{f.read_text(encoding='utf-8')}" for f in batch]
        )

        prompt = f"""
You are the "Second Brain" auditor. Analyze the following wiki notes and identify any contradictions, conflicting principles, or cognitive shifts between them.

CONTEXT:
{batch_content}

COMMAND: Identify contradictions.
- If notes from different dates or topics contradict each other, list the contradiction.
- For each identified contradiction, return it in this format:
  Contradiction: [Brief description]
  Sources: [[file1]], [[file2]]
  Suggestion: [How to resolve the contradiction or log it as a 'Cognitive Shift']

If no contradictions are found, return "No contradictions found."
"""

        try:
            if llm_provider == "mlx":
                url = os.environ.get(
                    "LLM_URL", "http://127.0.0.1:8080/v1/chat/completions"
                )
                payload = {
                    "model": llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "stream": False,
                }
                response = requests.post(url, json=payload, timeout=300)
                result = (
                    response.json()
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            else:
                logger.error("Only MLX provider supported for audits.")
                return

            if "No contradictions found" not in result:
                print(
                    f"\n--- POTENTIAL CONTRADICTIONS IN BATCH {i // batch_size + 1} ---\n{result}"
                )

        except Exception as e:
            logger.error(f"Error during contradiction audit: {e}")


if __name__ == "__main__":
    audit_contradictions()
