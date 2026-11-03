"""
Base AI Provider Interface and Exception Hierarchy.
Establishes a uniform contract for all model backends:
Groq, Google Gemini, xAI Grok, Ollama, and Fallback.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple


class ProviderError(Exception):
    """Base exception for provider failures."""
    pass


class ProviderAuthError(ProviderError):
    """Raised on 401 Unauthorized / invalid API key."""
    pass


class ProviderQuotaError(ProviderError):
    """Raised on 402/403 quota exceeded or billing inactive."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised on 429 Too Many Requests."""
    pass


class ProviderTimeoutError(ProviderError):
    """Raised when the LLM API request times out."""
    pass


class InvalidModelError(ProviderError):
    """Raised when the requested model identifier does not exist on the provider."""
    pass


class ProviderConnectionError(ProviderError):
    """Raised on network unreachable / DNS failure."""
    pass


class BaseAIProvider(ABC):
    """Abstract Base Class for AI Model Providers."""

    def __init__(self, name: str, model: str, api_key: str = "", timeout: float = 30.0):
        self.name = name
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        """Sends chat completion messages to the provider and returns text response."""
        pass

    @abstractmethod
    def health_check(self) -> Tuple[bool, str]:
        """Validates API connectivity and authentication with a lightweight probe."""
        pass

    def is_configured(self) -> bool:
        """Checks if minimal configuration is present."""
        return bool(self.api_key and "your_" not in self.api_key.lower())
