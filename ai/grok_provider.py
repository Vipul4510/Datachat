"""
xAI Grok Provider implementation.
Direct integration with official xAI Grok API: https://api.x.ai/v1/chat/completions
Supported models: grok-2-latest, grok-beta, grok-2-vision-1212.
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

VALID_GROK_MODELS = [
    "grok-2-latest",
    "grok-beta",
    "grok-2-1212"
]


class GrokProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "grok-2-latest", timeout: float = 30.0):
        if not model or "llama" in model.lower():
            model = "grok-2-latest"
        super().__init__(name="xAI Grok", model=model, api_key=api_key, timeout=timeout)
        self.endpoint = "https://api.x.ai/v1/chat/completions"

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        if not self.is_configured():
            raise ProviderAuthError("xAI Grok API key is not configured. Please set XAI_API_KEY in your settings.")

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
                    raise ProviderAuthError("xAI Grok authentication failed: Invalid or expired XAI_API_KEY.")
                elif resp.status_code == 403:
                    raise ProviderQuotaError("xAI Grok account quota exceeded or billing inactive.")
                elif resp.status_code == 429:
                    raise ProviderRateLimitError("xAI Grok rate limit reached. Please back off.")
                elif resp.status_code == 404 or (resp.status_code == 400 and "model" in resp.text.lower()):
                    raise InvalidModelError(f"xAI Grok model '{self.model}' not found. Available models: {', '.join(VALID_GROK_MODELS)}")
                elif resp.status_code >= 400:
                    raise ProviderError(f"xAI Grok API error ({resp.status_code}): {resp.text}")

                data = resp.json()
                return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"xAI Grok API request timed out after {self.timeout}s.")
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Could not connect to xAI Grok endpoint: {str(e)}")
        except (ProviderError, Exception):
            raise

    def health_check(self) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "XAI_API_KEY is not configured."
        try:
            res = self.complete([{"role": "user", "content": "ping"}], temperature=0.0)
            return True, f"Connected to xAI Grok ({self.model}). Response: {res[:30]}..."
        except Exception as e:
            return False, f"xAI Grok health check failed: {str(e)}"
