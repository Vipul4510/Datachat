"""
Groq API Provider implementation.
Uses Groq LPU inference with models like llama-3.3-70b-versatile, llama-3.1-8b-instant.
"""

import httpx
from typing import Dict, Any, List, Tuple
from ai.base_provider import (
    BaseAIProvider,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    InvalidModelError,
    ProviderConnectionError,
    ProviderError
)

VALID_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768"
]


class GroqProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b", timeout: float = 30.0):
        if not model:
            model = "openai/gpt-oss-120b"
        super().__init__(name="Groq", model=model, api_key=api_key, timeout=timeout)
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        if not self.is_configured():
            raise ProviderAuthError("Groq API key is not configured. Please add GROQ_API_KEY to your settings.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.endpoint, headers=headers, json=payload)
                if resp.status_code == 401:
                    raise ProviderAuthError("Groq authentication failed: Invalid or expired GROQ_API_KEY.")
                elif resp.status_code == 429:
                    raise ProviderRateLimitError("Groq rate limit reached. Please wait a moment or switch provider.")
                elif resp.status_code == 404 or (resp.status_code == 400 and "model" in resp.text.lower()):
                    raise InvalidModelError(f"Groq model '{self.model}' is not available. Try 'llama-3.3-70b-versatile'.")
                elif resp.status_code >= 400:
                    raise ProviderError(f"Groq API error (status {resp.status_code}): {resp.text}")

                data = resp.json()
                return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"Groq API request timed out after {self.timeout}s.")
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Could not connect to Groq API: {str(e)}")
        except (ProviderError, Exception):
            raise

    def health_check(self) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "GROQ_API_KEY is not configured."
        try:
            res = self.complete([{"role": "user", "content": "ping"}], temperature=0.0)
            return True, f"Connected to Groq ({self.model}). Response: {res[:30]}..."
        except Exception as e:
            return False, f"Groq health check failed: {str(e)}"
