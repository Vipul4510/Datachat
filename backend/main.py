"""
Main FastAPI Application Entry Point for DataChat.
Configures CORS middleware, loads environment variables, and includes API routers.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.routers.api import router as api_router

app = FastAPI(
    title="DataChat API",
    description="Conversational Data Analytics Using DuckDB & LLMs",
    version="1.0.0"
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
