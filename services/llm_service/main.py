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

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp
import asyncio
import json
import os
import io
import logging
import tempfile
import platform
import whisper
import pyttsx3
import scipy.io.wavfile
from scipy import signal
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_service")

# ── Voice Models (loaded once on startup) ─────────────────────────
# Whisper for ASR, pyttsx3 for TTS
WHISPER_MODEL = None
TTS_ENGINE = None
DEVICE = "cuda" if __import__("torch").cuda.is_available() else "cpu"
TTS_LOCK = asyncio.Lock()

def load_voice_models():
    """Load Whisper and TTS models on service startup."""
    global WHISPER_MODEL, TTS_ENGINE
    try:
        logger.info("Loading Whisper ASR model (tiny)...")
        WHISPER_MODEL = whisper.load_model("tiny", device=DEVICE)
        logger.info(f"Whisper tiny model loaded on {DEVICE}")
    except Exception as e:
        logger.error(f"Failed to load Whisper: {e}")
    
    try:
        logger.info("Initializing pyttsx3 TTS engine...")
        # Force espeak driver on Linux
        TTS_ENGINE = pyttsx3.init(driverName='espeak' if platform.system() == 'Linux' else None)
        # Set properties for better performance
        TTS_ENGINE.setProperty('rate', 150)  # Speed (words per minute)
        TTS_ENGINE.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
        logger.info(f"pyttsx3 TTS engine initialized with driver: {TTS_ENGINE.driverName if hasattr(TTS_ENGINE, 'driverName') else 'default'}")
    except Exception as e:
        logger.error(f"Failed to initialize TTS: {type(e).__name__}: {e}", exc_info=True)
        TTS_ENGINE = None


def _transcribe_audio_blocking(audio_data: np.ndarray) -> dict:
    """Runs Whisper transcription in a worker thread."""
    return WHISPER_MODEL.transcribe(audio_data, language="en")


def _synthesize_to_file_blocking(text: str, output_path: str):
    """Runs pyttsx3 synthesis in a worker thread with proper file sync."""
    import time
    TTS_ENGINE.save_to_file(text, output_path)
    TTS_ENGINE.runAndWait()
    # Give the system a moment to flush the file to disk
    time.sleep(0.5)
    # Verify file was actually created
    if not os.path.exists(output_path):
        raise RuntimeError(f"pyttsx3 failed to create output file: {output_path}")
    file_size = os.path.getsize(output_path)
    if file_size == 0:
        raise RuntimeError(f"pyttsx3 created empty file: {output_path}")
    logger.info(f"pyttsx3 synthesis complete: {output_path} ({file_size} bytes)")

app = FastAPI(title="LLM Service", version="1.0.0")

# ── CORS Configuration ───────────────────────────────────────────────
# Allow browser-based requests from the frontend for voice operations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load voice models on startup
@app.on_event("startup")
async def startup_event():
    """Load models when service starts."""
    load_voice_models()

# ── Request/Response Models ────────────────────────────────────────

class GenerateRequest(BaseModel):
    """Request schema for the /generate endpoint."""
    prompt: str
    model: str | None = None          # override model per-request
    temperature: float | None = 0.7
    max_tokens: int | None = 2048


class TranscribeResponse(BaseModel):
    """Response from /transcribe endpoint."""
    text: str
    language: str | None = None


class SynthesizeRequest(BaseModel):
    """Request schema for the /synthesize endpoint."""
    text: str
    language: str | None = "en"
    speaker: str | None = None


# ── Configuration ──────────────────────────────────────────────────
# The Ollama URL is configurable via environment variable so it works
# both locally and inside Docker (where Ollama runs on the host).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "phi3:latest")


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
                    whisper_status = "loaded" if WHISPER_MODEL else "not loaded"
                    tts_status = "initialized" if TTS_ENGINE else "not initialized"
                    return {
                        "status": "healthy",
                        "ollama": "connected",
                        "model": MODEL_NAME,
                        "whisper": whisper_status,
                        "tts": tts_status,
                    }
    except Exception:
        pass
    return {"status": "degraded", "ollama": "unreachable", "model": MODEL_NAME}


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    """
    Transcribe audio to text using Whisper ASR.
    
    Accepts:
      - WAV audio files (recommended)
    
    Returns:
      - Transcribed text and detected language
    
    Latency: ~2-5s for 10s audio on CPU (Whisper base model)
    """
    if WHISPER_MODEL is None:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")
    
    try:
        # Read file into memory
        contents = await file.read()
        logger.info(f"Received audio: {file.filename} ({len(contents)} bytes)")
        
        if len(contents) < 100:
            raise ValueError(f"Audio file too small ({len(contents)} bytes)")
        
        # Load WAV directly from bytes using scipy
        from scipy.io import wavfile as scipy_wavfile
        
        wav_bytes = io.BytesIO(contents)
        sample_rate, audio_data = scipy_wavfile.read(wav_bytes)
        logger.info(f"Loaded WAV: {sample_rate}Hz, shape={audio_data.shape}, dtype={audio_data.dtype}")
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        
        # Normalize to float32 in range [-1, 1]
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        else:
            audio_data = audio_data.astype(np.float32)
        
        # Resample to 16kHz if needed (Whisper expects 16kHz)
        target_sr = 16000
        if sample_rate != target_sr:
            logger.info(f"Resampling from {sample_rate}Hz to {target_sr}Hz...")
            # Calculate resampling ratio
            num_samples = int(len(audio_data) * target_sr / sample_rate)
            audio_data = signal.resample(audio_data, num_samples)
            logger.info(f"Resampled to {num_samples} samples at {target_sr}Hz")
        
        logger.info(f"Transcribing with Whisper (audio shape: {audio_data.shape})...")
        
        # Offload heavy ASR work so event loop stays responsive.
        result = await asyncio.to_thread(_transcribe_audio_blocking, audio_data)
        
        text = result.get("text", "").strip()
        logger.info(f"Transcription result: '{text}'")
        
        return TranscribeResponse(
            text=text,
            language=result.get("language", "en"),
        )
    
    except Exception as e:
        logger.error(f"Transcription error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthesize text to speech using pyttsx3 (system TTS).
    
    Parameters:
      - text: Text to synthesize
      - language: Language code (default: "en", pyttsx3 uses system locale)
      - speaker: Voice ID (optional, depends on system voices)
    
    Returns:
      - Audio file (WAV format on Linux)
    
    Latency: ~0.5-2s for typical sentence (very fast - uses system TTS)
    """
    if TTS_ENGINE is None:
        logger.error("TTS engine is None - initialization failed")
        raise HTTPException(status_code=503, detail="TTS engine not initialized")
    
    try:
        logger.info(f"Synthesizing text: {request.text[:50]}...")

        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        
        try:
            # pyttsx3 is not thread-safe; serialize calls and offload blocking work.
            async with TTS_LOCK:
                logger.info(f"Calling TTS synthesis to file: {tmp_path}")
                await asyncio.to_thread(_synthesize_to_file_blocking, request.text, tmp_path)
            
            logger.info(f"TTS file ready: {tmp_path}")
            
            # Return audio file with proper headers for range requests
            return FileResponse(
                tmp_path,
                media_type="audio/wav",
                filename="response.wav",
                headers={
                    "Content-Disposition": "inline; filename=response.wav",
                    "Accept-Ranges": "bytes",
                },
            )
        except Exception as e:
            # Clean up on error
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.error(f"TTS file processing error: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
