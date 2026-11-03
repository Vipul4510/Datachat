"""
Google Gemini Provider implementation.
Uses Google's official Generative Language API v1beta.
Supported models: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash.
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

VALID_GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp"
]


class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", timeout: float = 30.0):
        # Auto-correct invalid model identifier
        if not model or "2.5" in model:
            model = "gemini-1.5-flash"
        super().__init__(name="Google Gemini", model=model, api_key=api_key, timeout=timeout)

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        if not self.is_configured():
            raise ProviderAuthError("Gemini API key is not configured. Please add GEMINI_API_KEY to your settings.")

        # Transform messages into Gemini's contents schema
        gemini_contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                gemini_contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                gemini_contents.append({"role": "model", "parts": [{"text": content}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024
            }
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        headers = {"Content-Type": "application/json"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 400:
                    err_msg = resp.text.lower()
                    if "api_key" in err_msg or "invalid" in err_msg:
                        raise ProviderAuthError("Invalid Gemini API key provided.")
                    if "model" in err_msg or "not found" in err_msg:
                        raise InvalidModelError(f"Gemini model '{self.model}' was not found. Try 'gemini-1.5-flash'.")
                    raise ProviderError(f"Gemini 400 Bad Request: {resp.text}")
                elif resp.status_code in [401, 403]:
                    raise ProviderQuotaError(f"Gemini access denied / quota exhausted ({resp.status_code}): {resp.text}")
                elif resp.status_code == 429:
                    raise ProviderRateLimitError("Gemini rate limit exceeded. Please back off.")
                elif resp.status_code >= 500:
                    raise ProviderError(f"Gemini service unavailable ({resp.status_code}).")

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ProviderError("Gemini returned empty candidate response.")

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts or "text" not in parts[0]:
                    raise ProviderError("Gemini response contained no text part.")

                return parts[0]["text"]

        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"Gemini API request timed out after {self.timeout}s.")
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Could not connect to Gemini API: {str(e)}")
        except (ProviderError, Exception):
            raise

    def health_check(self) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "GEMINI_API_KEY is not configured."
        try:
            res = self.complete([{"role": "user", "content": "ping"}], temperature=0.0)
            return True, f"Connected to Gemini ({self.model}). Response: {res[:30]}..."
        except Exception as e:
            return False, f"Gemini health check failed: {str(e)}"
