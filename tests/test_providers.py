"""
Tests for Provider Architecture, Diagnostics, and Offline Fallback.
"""

import pytest
from ai.base_provider import (
    BaseAIProvider,
    ProviderAuthError,
    ProviderTimeoutError,
    InvalidModelError
)
from ai.fallback_provider import DeterministicFallbackProvider
from ai.groq_provider import GroqProvider
from ai.grok_provider import GrokProvider
from ai.gemini_provider import GeminiProvider
from ai.ollama_provider import OllamaProvider
from ai.provider_factory import (
    get_available_providers,
    resolve_provider,
    set_active_provider,
    get_provider_diagnostics
)


def test_deterministic_fallback_provider_synthesize():
    prov = DeterministicFallbackProvider()
    schema = [
        {"column_name": "region", "column_type": "VARCHAR", "sample_values": ["North", "South"]},
        {"column_name": "revenue", "column_type": "DOUBLE", "sample_values": [100.5, 200.0]}
    ]

    # Test count
    sql, _ = prov.synthesize_sql("How many orders exist?", "tbl_sales", schema)
    assert "COUNT(*)" in sql

    # Test total
    sql, _ = prov.synthesize_sql("What is the total revenue by region?", "tbl_sales", schema)
    assert "SUM" in sql
    assert "region" in sql

    # Test top-N
    sql, _ = prov.synthesize_sql("Show top 5 orders by revenue", "tbl_sales", schema)
    assert "ORDER BY" in sql
    assert "LIMIT 5" in sql


def test_provider_resolution_offline_fallback():
    prov, status = resolve_provider("fallback")
    assert isinstance(prov, DeterministicFallbackProvider)
    assert prov.is_configured() is True


def test_provider_diagnostics_structure():
    diags = get_provider_diagnostics()
    assert len(diags) >= 5
    names = [d["name"] for d in diags]
    assert "Groq" in names
    assert "Google Gemini" in names
    assert "xAI Grok" in names
    assert "Ollama (Local Backend)" in names or "Ollama (Local)" in [d.get("name") for d in diags]


def test_groq_missing_key_raises_auth_error():
    prov = GroqProvider(api_key="")
    with pytest.raises(ProviderAuthError):
        prov.complete([{"role": "user", "content": "hi"}])


def test_grok_missing_key_raises_auth_error():
    prov = GrokProvider(api_key="")
    with pytest.raises(ProviderAuthError):
        prov.complete([{"role": "user", "content": "hi"}])


def test_gemini_missing_key_raises_auth_error():
    prov = GeminiProvider(api_key="")
    with pytest.raises(ProviderAuthError):
        prov.complete([{"role": "user", "content": "hi"}])
