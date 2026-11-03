"""
Configuration and settings management for DataChat.
Loads settings from environment variables and local .env files safely.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

def load_environment():
    """Searches for .env in current working dir, parent, or backend/."""
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "backend", ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"),
    ]
    for p in candidates:
        if os.path.exists(p):
            load_dotenv(p, override=True)
            return p
    load_dotenv(override=True)
    return None

# Initial load
_loaded_env_path = load_environment()


class Settings:
    """Central configuration class."""
    
    @classmethod
    def reload(cls):
        load_environment()

    @property
    def groq_api_key(self) -> str:
        key = os.getenv("GROQ_API_KEY", "").strip()
        if "your_groq" in key.lower():
            return ""
        return key

    @property
    def groq_model(self) -> str:
        val = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        return val if val else "openai/gpt-oss-120b"

    @property
    def gemini_api_key(self) -> str:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if "your_gemini" in key.lower():
            return ""
        return key

    @property
    def gemini_model(self) -> str:
        val = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        if not val or "2.5" in val:
            return "gemini-1.5-flash"
        return val

    @property
    def xai_api_key(self) -> str:
        # Support both XAI_API_KEY and GROK_API_KEY
        key = (os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY") or "").strip()
        if "your_xai" in key.lower() or "your_grok" in key.lower():
            return ""
        return key

    @property
    def xai_model(self) -> str:
        return os.getenv("XAI_MODEL", os.getenv("GROK_MODEL", "grok-2-latest")).strip()

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()

    @property
    def ollama_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "llama3.2").strip()

    @property
    def default_provider(self) -> str:
        return os.getenv("DEFAULT_PROVIDER", "auto").strip().lower()

    @property
    def max_retries(self) -> int:
        try:
            return int(os.getenv("MAX_RETRIES", "1"))
        except ValueError:
            return 1

    @property
    def max_row_limit(self) -> int:
        try:
            return int(os.getenv("MAX_ROW_LIMIT", "500"))
        except ValueError:
            return 500

    @property
    def query_timeout_seconds(self) -> float:
        try:
            return float(os.getenv("QUERY_TIMEOUT_SECONDS", "15.0"))
        except ValueError:
            return 15.0

    @property
    def max_file_size_mb(self) -> int:
        try:
            return int(os.getenv("MAX_FILE_SIZE_MB", "200"))
        except ValueError:
            return 200

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Returns diagnostic status of all supported providers without exposing full keys."""
        return {
            "groq": {
                "name": "Groq (LPU Inference)",
                "configured": bool(self.groq_api_key),
                "model": self.groq_model,
                "key_preview": f"{self.groq_api_key[:6]}...{self.groq_api_key[-4:]}" if len(self.groq_api_key) > 10 else ("Configured" if self.groq_api_key else "Missing"),
                "is_active": False,
            },
            "gemini": {
                "name": "Google Gemini",
                "configured": bool(self.gemini_api_key),
                "model": self.gemini_model,
                "key_preview": f"{self.gemini_api_key[:6]}...{self.gemini_api_key[-4:]}" if len(self.gemini_api_key) > 10 else ("Configured" if self.gemini_api_key else "Missing"),
                "is_active": False,
            },
            "grok": {
                "name": "xAI Grok",
                "configured": bool(self.xai_api_key),
                "model": self.xai_model,
                "key_preview": f"{self.xai_api_key[:6]}...{self.xai_api_key[-4:]}" if len(self.xai_api_key) > 10 else ("Configured" if self.xai_api_key else "Missing"),
                "is_active": False,
            },
            "ollama": {
                "name": "Ollama (Local Backend)",
                "configured": True,  # URL-based
                "model": self.ollama_model,
                "endpoint": self.ollama_base_url,
                "is_active": False,
            },
            "fallback": {
                "name": "Deterministic Fallback (No-API Mode)",
                "configured": True,
                "model": "Rule-Based Analytical Parser",
                "key_preview": "N/A (Offline)",
                "is_active": False,
            }
        }


settings = Settings()
