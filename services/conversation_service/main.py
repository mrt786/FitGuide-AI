"""
<<<<<<< HEAD
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
=======
Conversation Service - Microservice for prompt orchestration with stateless backend semantics.

All session and benchmark state is stored in Redis. The API process keeps no in-memory
conversation state, so instances can scale horizontally and restart without losing session data.
>>>>>>> 32052ba (pushed the missing files)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
<<<<<<< HEAD
from typing import Dict
=======
>>>>>>> 32052ba (pushed the missing files)
import aiohttp
import asyncio
import json
import os
import logging
import re
import time
<<<<<<< HEAD
=======
from redis.asyncio import Redis
>>>>>>> 32052ba (pushed the missing files)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("conversation_service")

<<<<<<< HEAD
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
=======
app = FastAPI(title="Conversation Service", version="1.1.0")

LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))

MAX_RECENT_MESSAGES = 20
MAX_MEMORY_BULLETS = 60
MAX_BENCHMARK_ROWS = 100
LOCK_TTL_SECONDS = 120

SYSTEM_PROMPT_TEMPLATE = """You are FitGuide AI, a direct and professional gym coaching assistant.

Response policy (CRITICAL - ALWAYS FOLLOW):
- Default to 2-3 short, direct sentences.
- If the user explicitly asks for a workout routine or plan, provide a complete plan in 6-10 short lines.
- Give only the most immediately useful next actions.
- No fluff, no repetition, no motivational filler.
- If asking a clarifying question, ask only ONE, directly.
- Always use BOTH recent conversation and memory for continuity.
- Never repeat questions already answered in profile or memory.
- Treat stored profile facts as authoritative; do not challenge or re-ask them.
- Only ask for missing information that is truly necessary for the current response.
- If required info is missing, ask for that missing item directly in one sentence.
- Do NOT use formatting markers like [PLAN], [CUES], [SAFETY], etc. Write plain text only.
- Do not output bracketed tags of any kind.
- If the user asks for non-fitness topics (job, career, exams, coding, etc.), respond in one short sentence that you only handle fitness and ask one fitness-related follow-up.

Profile extraction policy:
- Actively extract user profile information from conversation.
- Extract and remember: goal, experience, age, weight, injury.
- Do not print internal tags, markers, or metadata in the user-facing reply.
>>>>>>> 32052ba (pushed the missing files)

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

<<<<<<< HEAD
=======
CONVERSATION_SUMMARY_PROMPT_TEMPLATE = """You are a memory compressor for a fitness assistant.
Summarize the entire conversation into 3-5 key bullets (max 15 words each).
Focus on: user's goals, current progress, important constraints, key achievements.
Keep only the most durable, actionable information.

Recent conversation:
{history}

Key takeaways:"""

>>>>>>> 32052ba (pushed the missing files)
SAFETY_SIGNAL_PATTERN = re.compile(
    r"\b(pain|injury|injured|dizzy|dizziness|fainted|chest pain|shortness of breath|severe)\b",
    re.IGNORECASE,
)

<<<<<<< HEAD

# ── Data Models ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat request from the gateway."""
=======
FITNESS_SIGNAL_PATTERN = re.compile(
    r"\b(fitness|workout|exercise|gym|weight|muscle|cardio|fat|diet|calorie|injury|training|routine|plan|lose|gain)\b",
    re.IGNORECASE,
)

NON_FITNESS_SIGNAL_PATTERN = re.compile(
    r"\b(job|career|resume|interview|exam|assignment|coding|programming|finance|stocks|crypto)\b",
    re.IGNORECASE,
)

PROFILE_UPDATE_PATTERN = re.compile(
    r"\[PROFILE_UPDATE:\s*([^]]+)\]",
    re.IGNORECASE,
)

PROFILE_UPDATE_STRIP_PATTERN = re.compile(
    r"\[PROFILE_UPDATE[^\]]*\]",
    re.IGNORECASE,
)

FORMATTING_MARKER_PATTERN = re.compile(
    r"\[/?(?:PLAN|CUES|SAFETY|RESPONSE|RESPONENT)[^\]]*\]|\[[A-Z_ ]{2,}[^\]]*\]:?|\{\s*\}",
    re.IGNORECASE,
)

NOISY_ARTIFACT_PATTERN = re.compile(
    r"(?:\b[0-9a-f]{8,}_[^\s]+\.(?:jpg|jpeg|png|gif|webp)\b|\b[0-9a-f]{12,}\b)",
    re.IGNORECASE,
)

redis_client: Redis | None = None


class ChatRequest(BaseModel):
>>>>>>> 32052ba (pushed the missing files)
    session_id: str
    message: str


class SessionInfo(BaseModel):
<<<<<<< HEAD
    """Response model for session info."""
=======
>>>>>>> 32052ba (pushed the missing files)
    session_id: str
    message_count: int
    profile: dict
    recent_history: list[dict]
    recent_history_count: int
    memory_count: int
    memory: list[str]


class BenchmarkInfo(BaseModel):
<<<<<<< HEAD
    """Latency benchmark stats per session."""
=======
>>>>>>> 32052ba (pushed the missing files)
    session_id: str
    turns: int
    avg_ttft_ms: float
    avg_total_latency_ms: float
    avg_tokens: float
    last_turn: dict | None = None


<<<<<<< HEAD
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
=======
class CheckpointRequest(BaseModel):
    name: str | None = "latest"


def session_key(session_id: str) -> str:
    return f"fitguide:session:{session_id}"


def metrics_key(session_id: str) -> str:
    return f"fitguide:metrics:{session_id}"


def lock_key(session_id: str) -> str:
    return f"fitguide:lock:{session_id}"


def checkpoint_key(session_id: str, name: str) -> str:
    return f"fitguide:checkpoint:{session_id}:{name}"


def default_session() -> dict:
    return {
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


def require_redis() -> Redis:
    if redis_client is None:
        raise HTTPException(status_code=503, detail="State store unavailable")
    return redis_client


async def load_session(session_id: str) -> dict:
    client = require_redis()
    raw = await client.get(session_key(session_id))
    if not raw:
        session = default_session()
        await save_session(session_id, session)
        return session

    try:
        session = json.loads(raw)
    except json.JSONDecodeError:
        session = default_session()
        await save_session(session_id, session)
    return session


async def save_session(session_id: str, session: dict):
    client = require_redis()
    await client.set(session_key(session_id), json.dumps(session), ex=SESSION_TTL_SECONDS)


async def delete_session_data(session_id: str):
    client = require_redis()
    await client.delete(session_key(session_id))
    await client.delete(metrics_key(session_id))


async def acquire_turn_lock(session_id: str) -> bool:
    client = require_redis()
    return await client.set(lock_key(session_id), "1", ex=LOCK_TTL_SECONDS, nx=True) is True


async def release_turn_lock(session_id: str):
    client = require_redis()
    await client.delete(lock_key(session_id))


def add_to_recent_history(session: dict, role: str, content: str):
>>>>>>> 32052ba (pushed the missing files)
    session["recent_history"].append({"role": role, "content": content})
    session["recent_history"] = session["recent_history"][-MAX_RECENT_MESSAGES:]


def compact_text(text: str, max_words: int = 28) -> str:
<<<<<<< HEAD
    """Fallback compaction when summarization model is unavailable."""
=======
>>>>>>> 32052ba (pushed the missing files)
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    words = cleaned.split(" ")
    compact = " ".join(words[:max_words])
    if len(words) > max_words:
        compact += "..."
    return compact


<<<<<<< HEAD
async def generate_short_text(prompt: str, max_tokens: int = 64, temperature: float = 0.1) -> str:
    """Calls /generate and returns a short text response by joining streamed tokens."""
=======
def extract_and_update_profile(session: dict, assistant_message: str) -> str:
    match = PROFILE_UPDATE_PATTERN.search(assistant_message)
    if match:
        updates_str = match.group(1).strip()
        updates = {}
        for pair in updates_str.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if key in ["goal", "experience", "age", "weight", "injury"]:
                    updates[key] = value
        if updates:
            for key, value in updates.items():
                session["profile"][key] = value
        assistant_message = PROFILE_UPDATE_PATTERN.sub("", assistant_message)

    return normalize_response_text(assistant_message)


def update_profile_from_user_message(session: dict, user_message: str):
    """Fallback profile extraction from user text so memory does not depend on model tags."""
    text = (user_message or "").strip().lower()
    if not text:
        return

    profile = session["profile"]

    age_match = re.search(r"\b(?:i\s*am|i'm|im)?\s*(\d{1,2})\s*(?:years?\s*old|yo|y/o)?\b", text)
    if age_match:
        age_value = int(age_match.group(1))
        if 12 <= age_value <= 100:
            profile["age"] = str(age_value)

    weight_match = re.search(r"\b(\d{2,3})\s*(kg|kgs|kilograms?|lb|lbs|pounds?)\b", text)
    if weight_match:
        profile["weight"] = f"{weight_match.group(1)} {weight_match.group(2)}"

    if re.search(r"\b(beginner|new to gym|newbie|no experience)\b", text):
        profile["experience"] = "beginner"
    elif re.search(r"\b(intermediate)\b", text):
        profile["experience"] = "intermediate"
    elif re.search(r"\b(advanced|experienced)", text):
        profile["experience"] = "advanced"

    if re.search(r"\b(lose weight|loose weight|fat loss|weight loss|cutting|slim down|reduce weight)\b", text):
        profile["goal"] = "lose weight"
    elif re.search(r"\b(build muscle|gain muscle|hypertrophy|bulk|bulking)\b", text):
        profile["goal"] = "build muscle"
    elif re.search(r"\b(fitness|stay fit|general health|healthy lifestyle)\b", text):
        profile["goal"] = "general fitness"

    if re.search(r"\b(no injury|no injuries|not injured|none|no pain)\b", text):
        profile["injury"] = "none"
    else:
        injury_match = re.search(
            r"\b(?:my\s+)?(knee|back|shoulder|elbow|wrist|ankle|hip|neck|chest)\b[^.\n]{0,24}\b(?:pain|injury|injured|hurts?|problem|issue)\b",
            text,
        )
        if injury_match:
            profile["injury"] = injury_match.group(0).strip(" .,")
        else:
            generic_injury = re.search(
                r"\b(?:injury|injured|pain|hurt|problem|issue)\b[:\s-]*(.{0,60})",
                text,
            )
            if generic_injury and generic_injury.group(1).strip():
                profile["injury"] = generic_injury.group(1).strip(" .,")


def upsert_memory_fact(session: dict, fact: str):
    """Insert high-signal deterministic facts while deduplicating."""
    fact = (fact or "").strip()
    if not fact:
        return

    existing = session.get("memory", [])
    low = fact.lower()
    if any((item or "").strip().lower() == low for item in existing):
        return

    existing.append(fact)
    session["memory"] = existing[-MAX_MEMORY_BULLETS:]


def persist_profile_facts_to_memory(session: dict):
    """Make core profile facts durable across long chats even after history truncation."""
    profile = session.get("profile", {})
    if profile.get("goal"):
        upsert_memory_fact(session, f"Goal: {profile['goal']}")
    if profile.get("age"):
        upsert_memory_fact(session, f"Age: {profile['age']}")
    if profile.get("weight"):
        upsert_memory_fact(session, f"Current weight: {profile['weight']}")
    if profile.get("experience"):
        upsert_memory_fact(session, f"Experience: {profile['experience']}")
    if profile.get("injury"):
        upsert_memory_fact(session, f"Injury status: {profile['injury']}")


def get_missing_profile_fields(session: dict) -> list[str]:
    profile = session.get("profile", {})
    ordered_fields = ["goal", "experience", "age", "weight", "injury"]
    return [field for field in ordered_fields if not profile.get(field)]


def build_profile_status_block(session: dict) -> str:
    profile = session.get("profile", {})
    missing = get_missing_profile_fields(session)
    return f"""
Known Profile Facts:
Goal: {profile['goal'] or 'Not provided'}
Experience: {profile['experience'] or 'Not provided'}
Age: {profile['age'] or 'Not provided'}
Weight: {profile['weight'] or 'Not provided'}
Injury: {profile['injury'] or 'Not provided'}

Missing Profile Facts:
{', '.join(missing) if missing else 'None'}

Instruction:
- Use Known Profile Facts as authoritative.
- Do not ask for facts that are already known.
- Only ask about Missing Profile Facts if they are needed for the current answer.
"""


def apply_profile_updates(session: dict, updates: dict):
    """Validate and apply structured profile updates."""
    if not updates:
        return

    profile = session.get("profile", {})

    goal = updates.get("goal")
    if isinstance(goal, str) and goal.strip():
        profile["goal"] = goal.strip()[:80]

    experience = updates.get("experience")
    if isinstance(experience, str) and experience.strip():
        profile["experience"] = experience.strip().lower()[:40]

    age = updates.get("age")
    if age is not None:
        try:
            age_int = int(str(age).strip())
            if 12 <= age_int <= 100:
                profile["age"] = str(age_int)
        except (ValueError, TypeError):
            pass

    weight = updates.get("weight")
    if isinstance(weight, str) and weight.strip():
        profile["weight"] = weight.strip()[:40]

    injury = updates.get("injury")
    if isinstance(injury, str) and injury.strip():
        profile["injury"] = injury.strip()[:120]


def extract_json_object(text: str) -> dict | None:
    """Extract first JSON object from model output safely."""
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def should_attempt_llm_profile_extraction(user_message: str, session: dict) -> bool:
    """Use LLM extraction when signal is present."""
    text = (user_message or "").lower()
    cues = [
        "i am",
        "i'm",
        "years old",
        "kg",
        "lbs",
        "injury",
        "pain",
        "goal",
        "lose",
        "weight",
        "muscle",
        "beginner",
        "intermediate",
        "advanced",
    ]
    return any(cue in text for cue in cues)


def looks_like_workout_plan_request(user_message: str) -> bool:
    text = (user_message or "").lower()
    signals = [
        "plan",
        "routine",
        "workout",
        "schedule",
        "program",
        "split",
        "daily",
        "weekly",
        "sets",
        "reps",
        "exercise",
    ]
    return any(signal in text for signal in signals)


async def generate_short_text(prompt: str, max_tokens: int = 64, temperature: float = 0.1) -> str:
>>>>>>> 32052ba (pushed the missing files)
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


<<<<<<< HEAD
async def summarize_turn(session_id: str, user_message: str, assistant_message: str):
    """Compresses one conversation turn into a short memory bullet."""
    session = sessions.get(session_id)
    if not session:
        return

=======
async def update_profile_with_llm(session: dict, user_message: str):
    """LLM-first structured profile extraction with strict JSON contract."""
    if not should_attempt_llm_profile_extraction(user_message, session):
        return

    current = session.get("profile", {})
    extraction_prompt = f"""Extract profile fields from the latest user message.
Return ONLY valid JSON with keys: goal, experience, age, weight, injury.
Use null for unknown values. No markdown. No extra text.

Rules:
- Only update facts that are explicitly present or clearly implied by the user.
- Do not invent values.
- Prefer concise canonical values like "lose weight", "build muscle", "beginner".

Current profile:
goal={current.get('goal')}
experience={current.get('experience')}
age={current.get('age')}
weight={current.get('weight')}
injury={current.get('injury')}

Latest user message:
{user_message}
"""

    try:
        model_out = await generate_short_text(extraction_prompt, max_tokens=120, temperature=0.0)
        parsed = extract_json_object(model_out)
        if parsed:
            apply_profile_updates(session, parsed)
    except Exception as e:
        logger.warning(f"LLM profile extraction failed: {e}")


def get_safety_policy_hint(user_message: str) -> str:
    if SAFETY_SIGNAL_PATTERN.search(user_message or ""):
        return (
            "\nSafety override for this turn:\n"
            "- Prioritize immediate safety wording.\n"
            "- Suggest stopping exercise and consulting a licensed clinician.\n"
            "- Do not prescribe treatment or diagnose.\n"
        )
    return ""


def get_max_tokens_for_user_message(user_message: str) -> int:
    """Adaptive response length: short by default, longer for explicit plan/routine requests."""
    if looks_like_workout_plan_request(user_message):
        return 420
    return 110


def is_non_fitness_request(user_message: str) -> bool:
    text = user_message or ""
    return bool(NON_FITNESS_SIGNAL_PATTERN.search(text)) and not bool(FITNESS_SIGNAL_PATTERN.search(text))


def non_fitness_redirect_message() -> str:
    return "I can only help with fitness coaching. Share your fitness goal and I will give you a clear plan."


def sanitize_stream_token(token: str) -> str:
    token = NOISY_ARTIFACT_PATTERN.sub("", token or "")
    token = token.replace("_a.jpg-", "")
    return token


def normalize_response_text(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = PROFILE_UPDATE_STRIP_PATTERN.sub("", cleaned)
    cleaned = FORMATTING_MARKER_PATTERN.sub("", cleaned)
    cleaned = NOISY_ARTIFACT_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def response_looks_truncated(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if cleaned.endswith("..."):
        return True
    return cleaned[-1] not in ".!?"


async def complete_if_truncated(user_message: str, partial_response: str) -> str:
    if not response_looks_truncated(partial_response):
        return partial_response

    completion_prompt = f"""Continue this assistant reply naturally from where it ended.
Rules:
- Continue only, do not restart.
- Keep it concise and coherent.
- Do not add tags or metadata.

User message:
{user_message}

Partial assistant reply:
{partial_response}
"""

    try:
        tail = await generate_short_text(completion_prompt, max_tokens=80, temperature=0.2)
        tail = normalize_response_text(tail)
        if tail:
            return normalize_response_text(partial_response + " " + tail)
    except Exception as e:
        logger.warning(f"Continuation generation failed: {e}")
    return partial_response


def build_prompt(session: dict, user_message: str) -> str:
    profile = session["profile"]
    history = session["recent_history"]
    memory = session["memory"]
    safety_hint = get_safety_policy_hint(user_message)

    system_prompt = SYSTEM_PROMPT_TEMPLATE + safety_hint

    profile_section = build_profile_status_block(session)

    memory_section = "\nCompressed Memory (high-signal context):\n"
    if memory:
        for item in memory:
            memory_section += f"- {item}\n"
    else:
        memory_section += "- None yet\n"

    history_section = "\nRecent Conversation (verbatim, latest only):\n"
    for msg in history:
        history_section += f"{msg['role'].capitalize()}: {msg['content']}\n"

    return (
        system_prompt
        + profile_section
        + memory_section
        + history_section
        + f"\nCurrent User Message:\n{user_message}\n"
        + "\nAssistant:"
    )


async def stream_from_llm_service(prompt: str, max_tokens: int):
    payload = {
        "prompt": prompt,
        "temperature": 0.35,
        "max_tokens": max_tokens,
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
                    logger.error(f"LLM service error: {resp.status} - {error_text}")
                    yield json.dumps({"error": f"LLM service error: {resp.status}"}) + "\n"
                    return

                async for line in resp.content:
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue

                    if "token" in data:
                        yield json.dumps({"token": data["token"]}) + "\n"
                    if data.get("done"):
                        yield json.dumps({"done": True}) + "\n"
                        return
                    if "error" in data:
                        yield json.dumps({"error": data["error"]}) + "\n"
                        return

    except aiohttp.ClientError as e:
        logger.error(f"Cannot reach LLM service: {e}")
        yield json.dumps({"error": f"Cannot reach LLM service: {str(e)}"}) + "\n"
    except asyncio.TimeoutError:
        logger.error("LLM service request timed out")
        yield json.dumps({"error": "LLM service request timed out"}) + "\n"


async def summarize_turn(session: dict, user_message: str, assistant_message: str):
>>>>>>> 32052ba (pushed the missing files)
    summary_prompt = TURN_SUMMARY_PROMPT_TEMPLATE.format(
        user_message=user_message,
        assistant_message=assistant_message,
    )

    bullet = ""
    try:
        bullet = await generate_short_text(summary_prompt, max_tokens=48, temperature=0.0)
    except Exception as e:
<<<<<<< HEAD
        logger.warning(f"Turn summarization fallback for session {session_id}: {e}")
=======
        logger.warning(f"Turn summarization fallback: {e}")
>>>>>>> 32052ba (pushed the missing files)

    if not bullet:
        user_short = compact_text(user_message, max_words=14)
        assistant_short = compact_text(assistant_message, max_words=14)
        bullet = f"User: {user_short} | Coach: {assistant_short}".strip()

    bullet = compact_text(bullet, max_words=20)
    if not bullet:
        return

    session["memory"].append(bullet)
    session["memory"] = session["memory"][-MAX_MEMORY_BULLETS:]


<<<<<<< HEAD
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
=======
async def summarize_conversation(session: dict):
    if len(session["memory"]) < 5:
        return

    history_parts = []
    for msg in session["recent_history"][-10:]:
        history_parts.append(f"{msg['role'].capitalize()}: {msg['content']}")

    if session["memory"]:
        history_parts.extend([f"Previous: {mem}" for mem in session["memory"][-5:]])

    history_text = "\n".join(history_parts)
    summary_prompt = CONVERSATION_SUMMARY_PROMPT_TEMPLATE.format(history=history_text)

    try:
        summary = await generate_short_text(summary_prompt, max_tokens=120, temperature=0.0)
        if summary:
            summary_bullets = [line.strip("- •").strip() for line in summary.split("\n") if line.strip()]
            if summary_bullets:
                merged_memory = session["memory"][-20:] + summary_bullets[:8]
                deduped = []
                seen = set()
                for item in merged_memory:
                    key = item.lower().strip()
                    if key and key not in seen:
                        seen.add(key)
                        deduped.append(item)
                session["memory"] = deduped[-MAX_MEMORY_BULLETS:]
                logger.info(f"Compressed conversation; memory bullets now: {len(session['memory'])}")
    except Exception as e:
        logger.warning(f"Conversation summarization failed: {e}")


async def record_benchmark(session_id: str, ttft_ms: float | None, total_latency_ms: float, token_count: int):
    client = require_redis()
    metric = {
        "ttft_ms": float(ttft_ms) if ttft_ms is not None else None,
        "total_latency_ms": float(total_latency_ms),
        "token_count": int(token_count),
        "timestamp": int(time.time()),
    }

    key = metrics_key(session_id)
    await client.rpush(key, json.dumps(metric))
    await client.ltrim(key, -MAX_BENCHMARK_ROWS, -1)
    await client.expire(key, SESSION_TTL_SECONDS)


async def get_benchmark_rows(session_id: str) -> list[dict]:
    client = require_redis()
    rows_raw = await client.lrange(metrics_key(session_id), 0, -1)
    rows = []
    for item in rows_raw:
        try:
            rows.append(json.loads(item))
        except json.JSONDecodeError:
            continue
    return rows


@app.on_event("startup")
async def startup_event():
    global redis_client
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

    last_error = None
    for attempt in range(1, 11):
        try:
            await redis_client.ping()
            logger.info("Connected to Redis state store")
            return
        except Exception as e:
            last_error = e
            logger.warning(f"Redis not ready yet (attempt {attempt}/10): {e}")
            await asyncio.sleep(2)

    raise RuntimeError(f"Unable to connect to Redis at startup: {last_error}")


@app.on_event("shutdown")
async def shutdown_event():
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


@app.get("/health")
async def health():
    redis_status = "unknown"
    llm_status: dict | str = "unknown"

    try:
        client = require_redis()
        await client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"unreachable: {e}"

>>>>>>> 32052ba (pushed the missing files)
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(
                f"{LLM_SERVICE_URL}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
<<<<<<< HEAD
                llm_health = await resp.json()
                return {"status": "healthy", "llm_service": llm_health}
    except Exception as e:
        return {"status": "degraded", "llm_service": str(e)}
=======
                llm_status = await resp.json()
    except Exception as e:
        llm_status = str(e)

    if redis_status == "connected":
        return {"status": "healthy", "redis": redis_status, "llm_service": llm_status}
    return {"status": "degraded", "redis": redis_status, "llm_service": llm_status}
>>>>>>> 32052ba (pushed the missing files)


@app.post("/chat")
async def chat(request: ChatRequest):
<<<<<<< HEAD
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
=======
>>>>>>> 32052ba (pushed the missing files)
    session_id = request.session_id
    user_message = request.message

    if not user_message or not user_message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

<<<<<<< HEAD
    get_or_create_session(session_id)
    session_lock = get_session_lock(session_id)

    # Turn-taking policy: one active assistant turn per session.
    if session_lock.locked():
        raise HTTPException(status_code=409, detail="Previous turn still in progress for this session")

    await session_lock.acquire()
    add_to_recent_history(session_id, "user", user_message)

    prompt = build_prompt(session_id, user_message)
=======
    locked = await acquire_turn_lock(session_id)
    if not locked:
        raise HTTPException(status_code=409, detail="Previous turn still in progress for this session")

    session = await load_session(session_id)
    await update_profile_with_llm(session, user_message)
    update_profile_from_user_message(session, user_message)
    persist_profile_facts_to_memory(session)
    add_to_recent_history(session, "user", user_message)
    turn_count = len([msg for msg in session["recent_history"] if msg["role"] == "assistant"])
    prompt = build_prompt(session, user_message)
    max_tokens = get_max_tokens_for_user_message(user_message)
    non_fitness = is_non_fitness_request(user_message)
>>>>>>> 32052ba (pushed the missing files)

    async def response_stream():
        full_response = ""
        token_count = 0
        turn_start = time.perf_counter()
        first_token_time = None
        try:
<<<<<<< HEAD
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
=======
            if non_fitness:
                redirect = non_fitness_redirect_message()
                yield json.dumps({"token": redirect}) + "\n"
                yield json.dumps({"done": True}) + "\n"

                add_to_recent_history(session, "assistant", redirect)
                await summarize_turn(session, user_message, redirect)
                if turn_count > 0 and turn_count % 3 == 0:
                    await summarize_conversation(session)
                await save_session(session_id, session)
                await record_benchmark(session_id, 0.0, 0.0, 1)
                return

            async for chunk in stream_from_llm_service(prompt, max_tokens):
                data = json.loads(chunk)
                if "token" in data:
                    token = sanitize_stream_token(data["token"])
                    if not token:
                        continue
                    full_response += token
                    token_count += 1
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    yield json.dumps({"token": token}) + "\n"
                    continue

                if "error" in data:
                    yield chunk
                    return
                if data.get("done"):
                    break

            cleaned_response = extract_and_update_profile(session, full_response)
            if looks_like_workout_plan_request(user_message):
                cleaned_response = await complete_if_truncated(user_message, cleaned_response)

            if cleaned_response and len(cleaned_response) > len(full_response):
                extra_tail = cleaned_response[len(full_response):]
                if extra_tail.strip():
                    yield json.dumps({"token": extra_tail}) + "\n"

            yield json.dumps({"done": True}) + "\n"

            if cleaned_response:
                add_to_recent_history(session, "assistant", cleaned_response)
                await summarize_turn(session, user_message, cleaned_response)
                if turn_count > 0 and turn_count % 3 == 0:
                    await summarize_conversation(session)

            await save_session(session_id, session)
>>>>>>> 32052ba (pushed the missing files)

            total_latency_ms = (time.perf_counter() - turn_start) * 1000.0
            ttft_ms = None
            if first_token_time is not None:
                ttft_ms = (first_token_time - turn_start) * 1000.0
<<<<<<< HEAD
            record_benchmark(session_id, ttft_ms, total_latency_ms, token_count)
        finally:
            if session_lock.locked():
                session_lock.release()

    return StreamingResponse(
        response_stream(),
        media_type="application/x-ndjson",
    )
=======
            await record_benchmark(session_id, ttft_ms, total_latency_ms, token_count)
        finally:
            await release_turn_lock(session_id)

    return StreamingResponse(response_stream(), media_type="application/x-ndjson")
>>>>>>> 32052ba (pushed the missing files)


@app.get("/session/{session_id}")
async def get_session(session_id: str):
<<<<<<< HEAD
    """Returns session info for debugging / monitoring."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
=======
    client = require_redis()
    if not await client.exists(session_key(session_id)):
        raise HTTPException(status_code=404, detail="Session not found")

    session = await load_session(session_id)
>>>>>>> 32052ba (pushed the missing files)
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
<<<<<<< HEAD
    """Returns latency benchmark aggregates for a session."""
    rows = session_metrics.get(session_id, [])
=======
    rows = await get_benchmark_rows(session_id)
>>>>>>> 32052ba (pushed the missing files)
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
<<<<<<< HEAD
    """Deletes a session (used by the 'New' button in the frontend)."""
    if session_id in sessions:
        del sessions[session_id]
        session_metrics.pop(session_id, None)
        session_locks.pop(session_id, None)
        logger.info(f"Deleted session: {session_id}")
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")
=======
    client = require_redis()
    if not await client.exists(session_key(session_id)):
        raise HTTPException(status_code=404, detail="Session not found")

    await delete_session_data(session_id)
    logger.info(f"Deleted session: {session_id}")
    return {"status": "deleted", "session_id": session_id}


@app.post("/session/{session_id}/checkpoint")
async def create_checkpoint(session_id: str, request: CheckpointRequest):
    client = require_redis()
    if not await client.exists(session_key(session_id)):
        raise HTTPException(status_code=404, detail="Session not found")

    name = (request.name or "latest").strip() or "latest"
    session = await load_session(session_id)
    rows = await get_benchmark_rows(session_id)
    payload = {"session": session, "metrics": rows}
    await client.set(checkpoint_key(session_id, name), json.dumps(payload), ex=SESSION_TTL_SECONDS)
    return {"status": "checkpoint_created", "session_id": session_id, "name": name}


@app.post("/session/{session_id}/restore")
async def restore_checkpoint(session_id: str, request: CheckpointRequest):
    client = require_redis()
    name = (request.name or "latest").strip() or "latest"
    raw = await client.get(checkpoint_key(session_id, name))
    if not raw:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Checkpoint payload corrupted")

    session = payload.get("session")
    metrics = payload.get("metrics", [])
    if not isinstance(session, dict):
        raise HTTPException(status_code=500, detail="Invalid checkpoint session payload")

    await save_session(session_id, session)
    await client.delete(metrics_key(session_id))
    if isinstance(metrics, list) and metrics:
        for row in metrics[-MAX_BENCHMARK_ROWS:]:
            await client.rpush(metrics_key(session_id), json.dumps(row))
        await client.expire(metrics_key(session_id), SESSION_TTL_SECONDS)

    return {"status": "checkpoint_restored", "session_id": session_id, "name": name}
>>>>>>> 32052ba (pushed the missing files)


if __name__ == "__main__":
    import uvicorn
<<<<<<< HEAD
=======

>>>>>>> 32052ba (pushed the missing files)
    uvicorn.run(app, host="0.0.0.0", port=8002)
