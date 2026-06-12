import logging
import os

import config  # noqa: F401 — loads .env via config.load_env
from llm_provider import get_llm_response, model_name, provider_name

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_connection():
    provider = provider_name()
    model = model_name(provider)
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    llm_url = os.environ.get("LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")

    print(f"--- Connection Test ---")
    print(f"Provider: {provider}")

    prompt = "Hi, testing connection. Reply 'OK' if working."
    messages = [{"role": "user", "content": prompt}]

    try:
        if provider == "gemini":
            print(f"Model: {model}")
            print(f"API Key: {'Configured' if gemini_api_key else 'MISSING'}")
        else:
            print(f"Model: {model}")
            print(f"URL: {llm_url}")
        response_text = get_llm_response(messages, max_tokens=100)
        if not response_text:
            raise RuntimeError("No response returned by configured LLM provider.")

        print(f"\nResponse: {response_text}")
        if "OK" in response_text.upper():
            print("\nSUCCESS: Connection is working.")
        else:
            print("\nSUCCESS (Partial): Received response, but not the expected 'OK'.")

    except Exception as e:
        print(f"\nFAILURE: Connection failed with error: {e}")


if __name__ == "__main__":
    test_connection()
