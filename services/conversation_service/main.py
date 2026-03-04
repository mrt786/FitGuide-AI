"""
Conversation Service — Microservice for session management & prompt orchestration.

This service acts as the "Conversation Manager" in the architecture:
  Web UI → Gateway → [Conversation Service] → LLM Service → Ollama

Why a separate service?
  - Separates business logic (prompt design, session state, conversation
    policies) from the transport layer (WebSockets, HTTP) and the inference
    layer (Ollama).
  - Allows the conversation logic to evolve independently — new prompt
    templates, profiling strategies, or context-window management schemes
    don't require touching the gateway or the LLM wrapper.
  - Keeps the service stateless-friendly: session data lives in memory here
    but could be moved to Redis without changing other services.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import aiohttp
import asyncio
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("conversation_service")

app = FastAPI(title="Conversation Service", version="1.0.0")

# ── Configuration ──────────────────────────────────────────────────
# URL of the LLM Service (resolved via Docker networking or localhost).
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")

# Maximum number of history messages to retain per session.
# Keeps the context window manageable for small models.
MAX_HISTORY = 8


# ── Data Models ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat request from the gateway."""
    session_id: str
    message: str


class SessionInfo(BaseModel):
    """Response model for session info."""
    session_id: str
    message_count: int
    profile: dict


# ── Session Storage ────────────────────────────────────────────────
# In-memory session store. Each session holds a user profile and
# conversation history.  In production, this would be backed by Redis.

sessions: Dict[str, Dict] = {}


def get_or_create_session(session_id: str) -> dict:
    """
    Lazily creates a session on first access.
    
    The profile fields are used in prompt construction to personalize
    advice — the model sees them in the system prompt every turn.
    """
    if session_id not in sessions:
        sessions[session_id] = {
            "profile": {
                "goal": None,
                "experience": None,
                "age": None,
                "weight": None,
                "injury": None,
            },
            "history": [],
        }
        logger.info(f"Created new session: {session_id}")
    return sessions[session_id]


def add_to_history(session_id: str, role: str, content: str):
    """Appends a message and trims old messages to stay within MAX_HISTORY."""
    session = sessions[session_id]
    session["history"].append({"role": role, "content": content})
    # Sliding window: keep only the last MAX_HISTORY messages so the
    # prompt fits within the small model's context window.
    session["history"] = session["history"][-MAX_HISTORY:]


def build_prompt(session_id: str, user_message: str) -> str:
    """
    Constructs the full prompt sent to the LLM.
    
    Structure:
      1. System prompt — defines the chatbot's persona & rules.
      2. User profile  — personalizes the response.
      3. Conversation history — provides multi-turn context.
      4. Current message — the user's latest input.
    
    This is pure prompt orchestration — no tools, no RAG, as required.
    """
    session = sessions[session_id]
    profile = session["profile"]
    history = session["history"]

    system_prompt = """You are FitGuide AI, a professional gym coaching assistant.

Rules:
- Be motivational and supportive.
- Ask clarifying questions before giving plans.
- Provide structured workout plans (sets, reps, rest).
- Do NOT give medical advice.
- If injury is mentioned, suggest consulting a doctor.
- Keep answers concise but helpful.
"""

    profile_section = f"""
User Profile:
Goal: {profile['goal'] or 'Not provided'}
Experience: {profile['experience'] or 'Not provided'}
Age: {profile['age'] or 'Not provided'}
Weight: {profile['weight'] or 'Not provided'}
Injury: {profile['injury'] or 'Not provided'}
"""

    history_section = "\nRecent Conversation:\n"
    for msg in history:
        history_section += f"{msg['role'].capitalize()}: {msg['content']}\n"

    full_prompt = (
        system_prompt
        + profile_section
        + history_section
        + f"\nCurrent User Message:\n{user_message}\n"
        + "\nAssistant:"
    )
    return full_prompt


async def stream_from_llm_service(prompt: str):
    """
    Calls the LLM Service's /generate endpoint and yields tokens.
    
    Uses aiohttp for fully async I/O — the event loop is never blocked,
    so the server can handle many concurrent streaming sessions.
    """
    payload = {
        "prompt": prompt,
        "temperature": 0.7,
        "max_tokens": 512,
    }

    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                f"{LLM_SERVICE_URL}/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"LLM service error: {resp.status} — {error_text}")
                    yield json.dumps({"error": f"LLM service error: {resp.status}"}) + "\n"
                    return

                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            if "token" in data:
                                yield json.dumps({"token": data["token"]}) + "\n"
                            if data.get("done"):
                                yield json.dumps({"done": True}) + "\n"
                                return
                            if "error" in data:
                                yield json.dumps({"error": data["error"]}) + "\n"
                                return
                        except json.JSONDecodeError:
                            continue

    except aiohttp.ClientError as e:
        logger.error(f"Cannot reach LLM service: {e}")
        yield json.dumps({"error": f"Cannot reach LLM service: {str(e)}"}) + "\n"
    except asyncio.TimeoutError:
        logger.error("LLM service request timed out")
        yield json.dumps({"error": "LLM service request timed out"}) + "\n"


# ── Endpoints ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — also pings the LLM service."""
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(
                f"{LLM_SERVICE_URL}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                llm_health = await resp.json()
                return {"status": "healthy", "llm_service": llm_health}
    except Exception as e:
        return {"status": "degraded", "llm_service": str(e)}


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint — processes a user message and returns a streaming
    response of tokens.
    
    Flow:
      1. Get or create the session.
      2. Record the user message in history.
      3. Build the full prompt (system + profile + history + message).
      4. Stream tokens from the LLM service.
      5. Accumulate the full response and save it to history.
    
    The response is streamed as newline-delimited JSON so the gateway can
    forward each token to the WebSocket client in real time.
    """
    session_id = request.session_id
    user_message = request.message

    if not user_message or not user_message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    get_or_create_session(session_id)
    add_to_history(session_id, "user", user_message)

    prompt = build_prompt(session_id, user_message)

    async def response_stream():
        full_response = ""
        async for chunk in stream_from_llm_service(prompt):
            data = json.loads(chunk)
            if "token" in data:
                full_response += data["token"]
            yield chunk

        # Save the complete assistant response to history
        if full_response:
            add_to_history(session_id, "assistant", full_response)

    return StreamingResponse(
        response_stream(),
        media_type="application/x-ndjson",
    )


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Returns session info for debugging / monitoring."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        message_count=len(session["history"]),
        profile=session["profile"],
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Deletes a session (used by the 'New' button in the frontend)."""
    if session_id in sessions:
        del sessions[session_id]
        logger.info(f"Deleted session: {session_id}")
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")
