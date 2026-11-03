"""
Ollama Local Backend Provider.
Enables running private open-source models completely locally (e.g. llama3.2, mistral, qwen2.5-coder)
without sending data outside the user's local machine.
"""

import httpx
from typing import Dict, Any, List, Tuple
from ai.base_provider import (
    BaseAIProvider,
    ProviderTimeoutError,
    InvalidModelError,
    ProviderConnectionError,
    ProviderError
)


class OllamaProvider(BaseAIProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2", timeout: float = 60.0):
        super().__init__(name="Ollama (Local)", model=model, api_key="local", timeout=timeout)
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/api/chat"

    def is_configured(self) -> bool:
        # Ollama does not require an API key, just a running service
        return True

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.endpoint, json=payload)
                if resp.status_code == 404:
                    raise InvalidModelError(
                        f"Model '{self.model}' not found in local Ollama. Run 'ollama pull {self.model}' in your terminal."
                    )
                elif resp.status_code >= 400:
                    raise ProviderError(f"Ollama server returned error {resp.status_code}: {resp.text}")

                data = resp.json()
                return data.get("message", {}).get("content", "")

        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"Local Ollama inference timed out after {self.timeout}s.")
        except httpx.ConnectError:
            raise ProviderConnectionError(
                f"Could not connect to Ollama at {self.base_url}. Ensure the Ollama app or daemon is running."
            )
        except (ProviderError, Exception):
            raise

    def health_check(self) -> Tuple[bool, str]:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name") for m in resp.json().get("models", [])]
                    has_model = any(self.model in m for m in models)
                    status_text = f"Ollama is running. Available models: {', '.join(models) if models else 'None'}"
                    if not has_model and models:
                        status_text += f" (Note: target model '{self.model}' not pulled yet)."
                    return True, status_text
                return False, f"Ollama responded with status {resp.status_code}"
        except Exception as e:
            return False, f"Ollama daemon not reachable at {self.base_url} ({str(e)})"
