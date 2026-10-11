"""
Main FastAPI Application Entry Point for DataChat.
Configures CORS middleware, loads environment variables, and includes API routers.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

import logging
from contextlib import asynccontextmanager

from backend.routers.api import router as api_router

logger = logging.getLogger("uvicorn")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup check
    from backend.services.llm import get_env_config
    cfg = get_env_config()
    has_groq = bool(cfg["GROQ_API_KEY"]) and "your_groq" not in cfg["GROQ_API_KEY"].lower()
    has_gemini = bool(cfg["GEMINI_API_KEY"]) and "your_gemini" not in cfg["GEMINI_API_KEY"].lower()

    if not has_groq and not has_gemini:
        logger.warning(
            "\n" + "!" * 70 + "\n"
            "WARNING: No valid LLM API key configured in backend/.env!\n"
            "Please set GROQ_API_KEY or GEMINI_API_KEY in backend/.env for conversational queries.\n"
            + "!" * 70
        )
    else:
        active = []
        if has_groq:
            active.append(f"Groq ({cfg['GROQ_MODEL']})")
        if has_gemini:
            active.append(f"Gemini ({cfg['GEMINI_MODEL']})")
        logger.info(f"LLM Services ready: {', '.join(active)}")

    yield

app = FastAPI(
    title="DataChat API",
    description="Conversational Data Analytics Using DuckDB & LLMs",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (Vite default port 5173 / localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main router
app.include_router(api_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to DataChat API - Conversational Analytics Using DuckDB",
        "docs_url": "/docs",
        "health_check": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
