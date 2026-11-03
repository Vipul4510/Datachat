"""
AI Provider Factory and Lifecycle Manager.
Coordinates model backends, auto-discovery, live diagnostics,
and graceful degradation without ever crashing the application.
"""

from typing import Dict, Any, List, Optional, Tuple
from config.settings import settings
from ai.base_provider import BaseAIProvider
from ai.groq_provider import GroqProvider
from ai.grok_provider import GrokProvider
from ai.gemini_provider import GeminiProvider
from ai.ollama_provider import OllamaProvider
from ai.fallback_provider import DeterministicFallbackProvider

_active_provider_name: str = "auto"
_cached_providers: Dict[str, BaseAIProvider] = {}


def get_available_providers() -> Dict[str, BaseAIProvider]:
    """Instantiates and returns all supported provider implementations."""
    providers = {}

    # Groq
    providers["groq"] = GroqProvider(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        timeout=settings.query_timeout_seconds
    )

    # Google Gemini
    providers["gemini"] = GeminiProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=settings.query_timeout_seconds
    )

    # xAI Grok
    providers["grok"] = GrokProvider(
        api_key=settings.xai_api_key,
        model=settings.xai_model,
        timeout=settings.query_timeout_seconds
    )

    # Ollama
    providers["ollama"] = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.query_timeout_seconds
    )

    # Fallback
    providers["fallback"] = DeterministicFallbackProvider()

    return providers


def set_active_provider(name: str) -> None:
    """Sets the explicitly desired active provider ('auto', 'groq', 'gemini', 'grok', 'ollama', 'fallback')."""
    global _active_provider_name
    _active_provider_name = name.lower()


def get_active_provider_name() -> str:
    """Returns currently selected provider identifier."""
    return _active_provider_name


def resolve_provider(preferred: Optional[str] = None) -> Tuple[BaseAIProvider, str]:
    """
    Resolves the best available provider instance.
    Returns: (provider_instance, resolution_status_message)
    """
    providers = get_available_providers()
    target = (preferred or _active_provider_name).lower()

    if target in providers and target != "auto":
        provider = providers[target]
        if target == "fallback":
            return provider, "Offline Deterministic Mode explicitly selected."
        if provider.is_configured():
            return provider, f"Using explicitly configured provider: {provider.name} ({provider.model})."
        else:
            # Explicit provider not configured: explain and fall back
            fallback = providers["fallback"]
            return fallback, f"{provider.name} is not configured (missing API credentials). Active in Fallback mode."

    # 'auto' mode: try Groq -> Gemini -> xAI Grok -> Ollama -> Fallback
    priority = ["groq", "gemini", "grok"]
    for p_name in priority:
        candidate = providers[p_name]
        if candidate.is_configured():
            return candidate, f"Auto-selected configured provider: {candidate.name} ({candidate.model})."

    # Check Ollama
    ollama = providers["ollama"]
    ok, _ = ollama.health_check()
    if ok:
        return ollama, f"Auto-selected local backend: {ollama.name} ({ollama.model})."

    # Degraded fallback mode
    return providers["fallback"], "No remote LLM API key configured. Operating in Offline Fallback Analytics Mode."


def get_provider_diagnostics() -> List[Dict[str, Any]]:
    """Runs connectivity and configuration diagnostics across all providers."""
    providers = get_available_providers()
    results = []

    for key, prov in providers.items():
        if key == "fallback":
            results.append({
                "id": "fallback",
                "name": "Deterministic Fallback",
                "model": "Rule-Based Parser",
                "configured": True,
                "healthy": True,
                "status_message": "Ready (Built-in offline engine)"
            })
            continue

        configured = prov.is_configured()
        healthy = False
        message = "Missing API key in environment or settings"

        if configured:
            try:
                healthy, message = prov.health_check()
            except Exception as e:
                healthy = False
                message = f"Check failed: {str(e)}"

        results.append({
            "id": key,
            "name": prov.name,
            "model": prov.model,
            "configured": configured,
            "healthy": healthy,
            "status_message": message
        })

    return results
