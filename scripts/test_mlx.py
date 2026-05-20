import os
from pathlib import Path

import requests


def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_env(Path(".env"))


def test_mlx_connection():
    url = os.environ.get("LLM_URL")
    provider = os.environ.get("LLM_PROVIDER")
    # Use the specific ID found from /v1/models
    model = "mlx-community/gemma-4-e4b-it-4bit"

    print(f"Testing {provider} at {url} with model {model}...")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello!"},
        ],
        "temperature": 0.1,
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
        response.raise_for_status()
        data = response.json()
        print("Success!")
        print(f"Response: {data['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"Failed: {e}")


if __name__ == "__main__":
    test_mlx_connection()
