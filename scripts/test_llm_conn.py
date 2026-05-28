import json
import logging
import os
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Project root is one level up
WORKSPACE_PATH = Path(__file__).parent.parent


def load_env():
    env_path = WORKSPACE_PATH / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_env()


def get_gemini_response(messages, api_key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 100,
        },
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def test_connection():
    provider = os.environ.get("LLM_PROVIDER", "mlx").lower()
    model = os.environ.get("LLM_MODEL", "mlx-community/gemma-4-e4b-it-4bit")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    llm_url = os.environ.get("LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")

    print(f"--- Connection Test ---")
    print(f"Provider: {provider}")

    prompt = "Hi, testing connection. Reply 'OK' if working."
    messages = [{"role": "user", "content": prompt}]

    try:
        if provider == "gemini":
            print(f"Model: {gemini_model}")
            print(f"API Key: {'Configured' if gemini_api_key else 'MISSING'}")
            response_text = get_gemini_response(messages, gemini_api_key, gemini_model)
        else:
            print(f"Model: {model}")
            print(f"URL: {llm_url}")
            api_key = (
                os.environ.get("OPENAI_API_KEY")
                or os.environ.get("DEEPSEEK_API_KEY")
                or "no-key"
            )
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.post(llm_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            response_text = response.json()["choices"][0]["message"]["content"]

        print(f"\nResponse: {response_text}")
        if "OK" in response_text.upper():
            print("\nSUCCESS: Connection is working.")
        else:
            print("\nSUCCESS (Partial): Received response, but not the expected 'OK'.")

    except Exception as e:
        print(f"\nFAILURE: Connection failed with error: {e}")
        if "response" in locals() and hasattr(response, "text"):
            print(f"Response Body: {response.text}")


if __name__ == "__main__":
    test_connection()
