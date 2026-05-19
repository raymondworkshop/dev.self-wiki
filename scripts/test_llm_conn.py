import logging
import os
from pathlib import Path

import requests


# Simple .env loader
def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


workspace = Path("/Users/zhaowenlong/workspace/dev.self-wiki")
load_env(workspace / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection():
    provider = os.environ.get("LLM_PROVIDER", "mlx").lower()
    model = os.environ.get("LLM_MODEL", "")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    print(f"--- Configuration ---")
    print(f"Provider: {provider}")
    print(f"Model: {model}")

    if provider == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        print(f"URL: {url}")
    else:
        url = os.environ.get("LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")
        headers = {}
        print(f"URL: {url}")

    prompt = "Hi, testing connection. Reply 'OK' if working."
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "stream": False,
    }

    try:
        print(f"\nSending request...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()['choices'][0]['message']['content']}")
            print("\nSUCCESS: Connection is working.")
        else:
            print(f"Response Body: {response.text}")
            print("\nFAILURE: Connection failed.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    test_connection()
