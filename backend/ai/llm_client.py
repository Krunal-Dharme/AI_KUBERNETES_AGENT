import time

import httpx
from loguru import logger

from core.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 90


class LLMClientError(Exception):
    """Raised when the LLM client fails after retries."""


class OpenRouterClient:
    """HTTPX-based client for OpenRouter chat completions."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = OPENROUTER_BASE_URL,
    ) -> None:
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or settings.openrouter_model or DEFAULT_MODEL
        self.base_url = base_url.rstrip("/")

    def chat_completion(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise LLMClientError(
                "OPENROUTER_API_KEY is not configured. "
                "Add your InsForge-provisioned OpenRouter key to backend/.env"
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "AI Kubernetes Agent",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }

        last_error = "Unknown error"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    "Calling OpenRouter model '{}' (attempt {}/{})",
                    self.model,
                    attempt,
                    MAX_RETRIES,
                )

                with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    response = client.post(url, headers=headers, json=payload)

                if response.status_code == 429:
                    last_error = "Rate limited by OpenRouter"
                    logger.warning("OpenRouter rate limit hit, retrying...")
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                if response.status_code >= 500:
                    last_error = f"OpenRouter server error ({response.status_code})"
                    logger.warning("{}: {}", last_error, response.text[:200])
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                if response.status_code >= 400:
                    detail = response.text[:300]
                    logger.error("OpenRouter request failed ({}): {}", response.status_code, detail)
                    raise LLMClientError(
                        f"OpenRouter request failed with status {response.status_code}"
                    )

                data = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                if not content:
                    last_error = "Empty response from OpenRouter"
                    logger.warning("Empty LLM response, retrying...")
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                logger.info("OpenRouter response received successfully")
                return content

            except httpx.TimeoutException:
                last_error = f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s"
                logger.warning("OpenRouter timeout on attempt {}", attempt)
                time.sleep(RETRY_DELAY_SECONDS * attempt)

            except httpx.RequestError as exc:
                last_error = f"Network error: {exc}"
                logger.warning("OpenRouter network error on attempt {}: {}", attempt, exc)
                time.sleep(RETRY_DELAY_SECONDS * attempt)

        raise LLMClientError(f"OpenRouter failed after {MAX_RETRIES} attempts: {last_error}")
