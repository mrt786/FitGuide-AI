"""
LLM Service — Microservice that wraps the local Ollama LLM engine.

This service acts as the "Local LLM Engine" in the architecture:
  Web UI → Gateway → Conversation Manager → [LLM Service] → Ollama

Why a separate service?
  - Decouples the LLM inference layer from business logic.
  - Allows independent scaling (e.g., multiple LLM workers).
  - Makes it easy to swap Ollama for another backend (vLLM, llama.cpp)
    without touching other services.
  - Provides a clean internal API contract for streaming token generation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiohttp
import asyncio
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_service")

app = FastAPI(title="LLM Service", version="1.0.0")

# ── Configuration ──────────────────────────────────────────────────
# The Ollama URL is configurable via environment variable so it works
# both locally and inside Docker (where Ollama runs on the host).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "phi3:latest")


class GenerateRequest(BaseModel):
    """Request schema for the /generate endpoint."""
    prompt: str
    model: str | None = None          # override model per-request
    temperature: float | None = 0.7
    max_tokens: int | None = 512


async def stream_from_ollama(prompt: str, model: str, temperature: float, max_tokens: int):
    """
    Async generator that streams tokens from Ollama's /api/generate endpoint.
    
    Uses aiohttp instead of blocking requests so the event loop is never
    blocked — critical for handling multiple concurrent WebSocket users.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    logger.error(f"Ollama returned {resp.status}: {error_body}")
                    yield json.dumps({"error": f"Ollama error: {resp.status}"}) + "\n"
                    return

                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            token = data.get("response", "")
                            if token:
                                yield json.dumps({"token": token}) + "\n"
                            if data.get("done", False):
                                yield json.dumps({"done": True}) + "\n"
                                return
                        except json.JSONDecodeError:
                            continue

    except aiohttp.ClientError as e:
        logger.error(f"Connection error to Ollama: {e}")
        yield json.dumps({"error": f"LLM connection error: {str(e)}"}) + "\n"
    except asyncio.TimeoutError:
        logger.error("Ollama request timed out")
        yield json.dumps({"error": "LLM request timed out"}) + "\n"


# ── Endpoints ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — also verifies Ollama connectivity."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return {"status": "healthy", "ollama": "connected", "model": MODEL_NAME}
    except Exception:
        pass
    return {"status": "degraded", "ollama": "unreachable", "model": MODEL_NAME}


@app.post("/generate")
async def generate(request: GenerateRequest):
    """
    Streaming token generation endpoint.
    
    Returns a newline-delimited JSON stream where each line is either:
      {"token": "..."} — a generated token
      {"done": true}   — signals generation is complete
      {"error": "..."}  — an error occurred
    """
    model = request.model or MODEL_NAME

    return StreamingResponse(
        stream_from_ollama(request.prompt, model, request.temperature, request.max_tokens),
        media_type="application/x-ndjson",
    )
