"""
Gateway Service — Public-facing API microservice.

This service acts as the "FastAPI + WebSocket" layer in the architecture:
  Web UI → [Gateway Service] → Conversation Service → LLM Service → Ollama

Why a separate gateway?
  - Single entry point for all clients (browser, Postman, etc.).
  - Handles WebSocket upgrade and streaming — other services only need
    plain HTTP, keeping them simpler.
  - Serves the static frontend files.
  - Can add authentication, rate limiting, CORS, etc. without touching
    business logic or inference code.
  - Decouples the transport protocol (WebSocket) from the business layer.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp
import asyncio
import json
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway_service")

app = FastAPI(title="FitGuide AI Gateway", version="1.0.0")

# ── CORS ───────────────────────────────────────────────────────────
# Allow all origins during development.  In production, restrict this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configuration ──────────────────────────────────────────────────
CONVERSATION_SERVICE_URL = os.getenv(
    "CONVERSATION_SERVICE_URL", "http://localhost:8002"
)
LLM_SERVICE_URL = os.getenv(
    "LLM_SERVICE_URL", "http://localhost:8001"
)

# ── Static Files (Frontend) ───────────────────────────────────────
# Mounted at /static so CSS/JS can be loaded by the HTML page.
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ── REST Endpoints ─────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the chat UI."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "FitGuide AI Gateway is running. Connect via /ws/chat"}


@app.get("/health")
async def health():
    """
    Cascading health check — pings conversation service, which in turn
    pings the LLM service and Ollama.  Gives a full system status.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{CONVERSATION_SERVICE_URL}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                downstream = await resp.json()
                return {
                    "status": "healthy",
                    "gateway": "ok",
                    "downstream": downstream,
                }
    except Exception as e:
        return {
            "status": "degraded",
            "gateway": "ok",
            "downstream": str(e),
        }


# ── Active connections tracking ────────────────────────────────────
# Tracks how many WebSocket clients are connected — useful for monitoring.
active_connections: dict[str, WebSocket] = {}


@app.get("/connections")
async def get_connections():
    """Returns the number of active WebSocket connections."""
    return {"active_connections": len(active_connections)}


# ── Voice Proxy Endpoints ──────────────────────────────────────────
# Forward voice requests to the LLM service (avoids CORS issues)

@app.post("/transcribe")
async def transcribe_proxy(file: UploadFile = File(...)):
    """
    Proxy endpoint for audio transcription.
    
    Forwards the audio file to the LLM Service /transcribe endpoint.
    No CORS issues since this is same-origin (same as frontend).
    """
    try:
        logger.info(f"Gateway: Forwarding transcription request to LLM Service")
        
        # Read file contents
        contents = await file.read()
        
        # Create multipart form data for forwarding
        form_data = aiohttp.FormData()
        form_data.add_field('file', contents, filename=file.filename, content_type=file.content_type)
        
        # Forward to LLM service
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{LLM_SERVICE_URL}/transcribe",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"LLM Service transcribe error: {resp.status} - {error_text}")
                    raise HTTPException(status_code=resp.status, detail=error_text)
                
                result = await resp.json()
                logger.info(f"Gateway: Transcription successful: {result['text'][:100]}...")
                return result
    
    except Exception as e:
        logger.error(f"Gateway transcription proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize")
async def synthesize_proxy(request: dict):
    """
    Proxy endpoint for text-to-speech synthesis.
    
    Forwards the text to the LLM Service /synthesize endpoint.
    Returns audio file (no CORS issues).
    """
    try:
        logger.info(f"Gateway: Forwarding synthesis request to LLM Service")
        
        # Forward to LLM service
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{LLM_SERVICE_URL}/synthesize",
                json=request,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"LLM Service synthesize error: {resp.status} - {error_text}")
                    raise HTTPException(status_code=resp.status, detail=error_text)
                
                # Get audio content
                audio_data = await resp.read()
                content_type = resp.headers.get('Content-Type', 'audio/mpeg')
                
                logger.info(f"Gateway: Synthesis successful, returning {len(audio_data)} bytes")
                
                # Return audio file with proper headers
                return StreamingResponse(
                    iter([audio_data]),
                    media_type=content_type,
                    headers={"Content-Disposition": "inline; filename=response.mp3"}
                )
    
    except Exception as e:
        logger.error(f"Gateway synthesis proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── WebSocket Endpoint ─────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time chat.

    Protocol:
      Client → Server (JSON):  {"session_id": "...", "message": "..."}
      Server → Client (text):  token strings, or "[END]" to signal completion
      Server → Client (text):  "[ERROR] ..." on failures

    Each connection gets a unique internal ID for tracking.  The session_id
    in the message payload maps to a conversation session in the
    Conversation Service (different concept from the WS connection).

    Flow per message:
      1. Receive JSON from client.
      2. POST to Conversation Service /chat (streaming).
      3. Forward each token to the WebSocket as it arrives.
      4. Send "[END]" when the LLM finishes.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    active_connections[connection_id] = websocket
    logger.info(f"WebSocket connected: {connection_id} (total: {len(active_connections)})")

    try:
        while True:
            # ── Receive client message ──
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await websocket.send_text("[ERROR] Invalid JSON")
                await websocket.send_text("[END]")
                continue

            user_message = data.get("message", "").strip()
            session_id = data.get("session_id", connection_id)

            if not user_message:
                await websocket.send_text("[END]")
                continue

            # ── Forward to Conversation Service ──
            try:
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.post(
                        f"{CONVERSATION_SERVICE_URL}/chat",
                        json={"session_id": session_id, "message": user_message},
                        timeout=aiohttp.ClientTimeout(total=300),
                    ) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            logger.error(f"Conversation service error: {resp.status}")
                            await websocket.send_text(f"[ERROR] Service error: {resp.status}")
                            await websocket.send_text("[END]")
                            continue

                        # Stream tokens to the WebSocket client
                        async for line in resp.content:
                            if line:
                                try:
                                    chunk = json.loads(line.decode("utf-8"))
                                    if "token" in chunk:
                                        await websocket.send_text(chunk["token"])
                                    if "error" in chunk:
                                        await websocket.send_text(f"[ERROR] {chunk['error']}")
                                    if chunk.get("done"):
                                        break
                                except json.JSONDecodeError:
                                    continue

            except aiohttp.ClientError as e:
                logger.error(f"Cannot reach conversation service: {e}")
                await websocket.send_text("[ERROR] Service unavailable")
            except asyncio.TimeoutError:
                logger.error("Conversation service timed out")
                await websocket.send_text("[ERROR] Request timed out")

            # Signal end of response
            await websocket.send_text("[END]")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error {connection_id}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        active_connections.pop(connection_id, None)
        logger.info(f"Connection cleaned up: {connection_id} (total: {len(active_connections)})")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
