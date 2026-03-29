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
from typing import Dict
import aiohttp
import asyncio
import json
import os
import logging
import re
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("conversation_service")

app = FastAPI(title="Conversation Service", version="1.0.0")

# ── Configuration ──────────────────────────────────────────────────
# URL of the LLM Service (resolved via Docker networking or localhost).
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")

# Keep a very small verbatim window for immediate coherence.
MAX_RECENT_MESSAGES = 6
# Keep bounded compressed memory for older context.
MAX_MEMORY_BULLETS = 24

# Explicit prompt templates (deliverable requirement).
SYSTEM_PROMPT_TEMPLATE = """You are FitGuide AI, an ethical gym coaching assistant.

Response policy:
- Be concise: 4-8 short lines by default.
- Give only the most useful next steps.
- Use clear structure: Plan, Cues, Safety.
- Ask at most one clarifying question when required.

Ethics and safety policy:
- Never provide medical diagnosis or treatment.
- If pain, injury, dizziness, chest pain, or severe symptoms are mentioned, advise pausing and seeing a licensed clinician.
- Do not encourage unsafe, extreme, or deceptive behavior.

Style policy:
- Keep tone supportive and practical.
- Avoid long explanations, repetition, and filler.
- Stay focused on fitness coaching and user goals.
"""

TURN_SUMMARY_PROMPT_TEMPLATE = """You are a memory compressor for a fitness assistant.
Summarize this turn into ONE short bullet (max 18 words).
Keep only durable facts: goal, constraints, preferences, injury/safety notes, commitment.
Exclude fluff, greetings, and repetitive wording.
Return plain text only.

User: {user_message}
Assistant: {assistant_message}
"""

SAFETY_SIGNAL_PATTERN = re.compile(
    r"\b(pain|injury|injured|dizzy|dizziness|fainted|chest pain|shortness of breath|severe)\b",
    re.IGNORECASE,
)


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
    recent_history: list[dict]
    recent_history_count: int
    memory_count: int
    memory: list[str]


class BenchmarkInfo(BaseModel):
    """Latency benchmark stats per session."""
    session_id: str
    turns: int
    avg_ttft_ms: float
    avg_total_latency_ms: float
    avg_tokens: float
    last_turn: dict | None = None


# ── Session Storage ────────────────────────────────────────────────
# In-memory session store. Each session holds a user profile and
# conversation history.  In production, this would be backed by Redis.

sessions: Dict[str, Dict] = {}
session_locks: Dict[str, asyncio.Lock] = {}
session_metrics: Dict[str, list[dict]] = {}


def get_session_lock(session_id: str) -> asyncio.Lock:
    """Ensures turn-taking per session (one active generation at a time)."""
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    return session_locks[session_id]


def get_safety_policy_hint(user_message: str) -> str:
    """Injects extra safety guardrails when risk signals are present."""
    if SAFETY_SIGNAL_PATTERN.search(user_message or ""):
        return (
            "\\nSafety override for this turn:\n"
            "- Prioritize immediate safety wording.\\n"
            "- Suggest stopping exercise and consulting a licensed clinician.\\n"
            "- Do not prescribe treatment or diagnose.\\n"
        )
    return ""


def record_benchmark(session_id: str, ttft_ms: float | None, total_latency_ms: float, token_count: int):
    """Stores per-turn inference metrics for assignment benchmarking."""
    if session_id not in session_metrics:
        session_metrics[session_id] = []

    metric = {
        "ttft_ms": float(ttft_ms) if ttft_ms is not None else None,
        "total_latency_ms": float(total_latency_ms),
        "token_count": int(token_count),
        "timestamp": int(time.time()),
    }
    session_metrics[session_id].append(metric)
    session_metrics[session_id] = session_metrics[session_id][-100:]


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
            "recent_history": [],
            "memory": [],
        }
        logger.info(f"Created new session: {session_id}")
    return sessions[session_id]


def add_to_recent_history(session_id: str, role: str, content: str):
    """Adds raw turns to a short rolling window for immediate context."""
    session = sessions[session_id]
    session["recent_history"].append({"role": role, "content": content})
    session["recent_history"] = session["recent_history"][-MAX_RECENT_MESSAGES:]


def compact_text(text: str, max_words: int = 28) -> str:
    """Fallback compaction when summarization model is unavailable."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    words = cleaned.split(" ")
    compact = " ".join(words[:max_words])
    if len(words) > max_words:
        compact += "..."
    return compact


async def generate_short_text(prompt: str, max_tokens: int = 64, temperature: float = 0.1) -> str:
    """Calls /generate and returns a short text response by joining streamed tokens."""
    payload = {
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    output = ""
    async with aiohttp.ClientSession() as http_session:
        async with http_session.post(
            f"{LLM_SERVICE_URL}/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"Summary generation failed: {resp.status} - {error_text}")

            async for line in resp.content:
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                if "token" in data:
                    output += data["token"]
                if data.get("done"):
                    break
                if "error" in data:
                    raise RuntimeError(data["error"])

    return output.strip()


async def summarize_turn(session_id: str, user_message: str, assistant_message: str):
    """Compresses one conversation turn into a short memory bullet."""
    session = sessions.get(session_id)
    if not session:
        return

    summary_prompt = TURN_SUMMARY_PROMPT_TEMPLATE.format(
        user_message=user_message,
        assistant_message=assistant_message,
    )

    bullet = ""
    try:
        bullet = await generate_short_text(summary_prompt, max_tokens=48, temperature=0.0)
    except Exception as e:
        logger.warning(f"Turn summarization fallback for session {session_id}: {e}")

    if not bullet:
        user_short = compact_text(user_message, max_words=14)
        assistant_short = compact_text(assistant_message, max_words=14)
        bullet = f"User: {user_short} | Coach: {assistant_short}".strip()

    bullet = compact_text(bullet, max_words=20)
    if not bullet:
        return

    session["memory"].append(bullet)
    session["memory"] = session["memory"][-MAX_MEMORY_BULLETS:]


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
    history = session["recent_history"]
    memory = session["memory"]
    safety_hint = get_safety_policy_hint(user_message)

    system_prompt = SYSTEM_PROMPT_TEMPLATE + safety_hint

    profile_section = f"""
User Profile:
Goal: {profile['goal'] or 'Not provided'}
Experience: {profile['experience'] or 'Not provided'}
Age: {profile['age'] or 'Not provided'}
Weight: {profile['weight'] or 'Not provided'}
Injury: {profile['injury'] or 'Not provided'}
"""

    memory_section = "\nCompressed Memory (high-signal context):\n"
    if memory:
        for item in memory:
            memory_section += f"- {item}\n"
    else:
        memory_section += "- None yet\n"

    history_section = "\nRecent Conversation (verbatim, latest only):\n"
    for msg in history:
        history_section += f"{msg['role'].capitalize()}: {msg['content']}\n"

    full_prompt = (
        system_prompt
        + profile_section
        + memory_section
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
        "temperature": 0.35,
        "max_tokens": 220,
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
    session_lock = get_session_lock(session_id)

    # Turn-taking policy: one active assistant turn per session.
    if session_lock.locked():
        raise HTTPException(status_code=409, detail="Previous turn still in progress for this session")

    await session_lock.acquire()
    add_to_recent_history(session_id, "user", user_message)

    prompt = build_prompt(session_id, user_message)

    async def response_stream():
        full_response = ""
        token_count = 0
        turn_start = time.perf_counter()
        first_token_time = None
        try:
            async for chunk in stream_from_llm_service(prompt):
                data = json.loads(chunk)
                if "token" in data:
                    full_response += data["token"]
                    token_count += 1
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                yield chunk

            # Save the complete assistant response to history
            if full_response:
                add_to_recent_history(session_id, "assistant", full_response)

                # Summarize turn asynchronously to avoid adding user-visible latency.
                asyncio.create_task(summarize_turn(session_id, user_message, full_response))

            total_latency_ms = (time.perf_counter() - turn_start) * 1000.0
            ttft_ms = None
            if first_token_time is not None:
                ttft_ms = (first_token_time - turn_start) * 1000.0
            record_benchmark(session_id, ttft_ms, total_latency_ms, token_count)
        finally:
            if session_lock.locked():
                session_lock.release()

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
        message_count=len(session["recent_history"]),
        profile=session["profile"],
        recent_history=session["recent_history"],
        recent_history_count=len(session["recent_history"]),
        memory_count=len(session["memory"]),
        memory=session["memory"],
    )


@app.get("/benchmarks/{session_id}", response_model=BenchmarkInfo)
async def get_session_benchmarks(session_id: str):
    """Returns latency benchmark aggregates for a session."""
    rows = session_metrics.get(session_id, [])
    if not rows:
        raise HTTPException(status_code=404, detail="No benchmark data for session")

    ttft_values = [row["ttft_ms"] for row in rows if row.get("ttft_ms") is not None]
    total_values = [row["total_latency_ms"] for row in rows]
    token_values = [row["token_count"] for row in rows]

    avg_ttft = sum(ttft_values) / len(ttft_values) if ttft_values else 0.0
    avg_total = sum(total_values) / len(total_values) if total_values else 0.0
    avg_tokens = sum(token_values) / len(token_values) if token_values else 0.0

    return BenchmarkInfo(
        session_id=session_id,
        turns=len(rows),
        avg_ttft_ms=round(avg_ttft, 2),
        avg_total_latency_ms=round(avg_total, 2),
        avg_tokens=round(avg_tokens, 2),
        last_turn=rows[-1],
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Deletes a session (used by the 'New' button in the frontend)."""
    if session_id in sessions:
        del sessions[session_id]
        session_metrics.pop(session_id, None)
        session_locks.pop(session_id, None)
        logger.info(f"Deleted session: {session_id}")
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
