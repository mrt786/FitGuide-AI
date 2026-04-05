# FitGuide AI – Gym Coaching Assistant

FitGuide AI is a conversational gym coaching assistant powered by a local LLM (Phi-3) via Ollama. It provides personalized workout plans, motivational support, and fitness guidance through a real-time chat interface built with FastAPI WebSockets.

## Features

- **Real-time streaming chat** – Responses are streamed token-by-token over WebSockets for a smooth experience.
- **Voice Interface (NEW)** – Speech-to-text (Whisper ASR) and text-to-speech (pyttsx3) for hands-free interaction.
- **Voice Recording & Playback** – Record audio messages and receive audio responses automatically.
- **Session management** – Each connection gets a unique session with conversation history and user profile tracking.
- **User profiling** – Tracks fitness goal, experience level, age, weight, and injury status to personalize advice.
- **Local & private** – Runs entirely on your machine using Ollama, Whisper, and pyttsx3; no external APIs; no data leaves your system.
- **Microservices architecture** – Three independent containerized services communicating over HTTP.
- **Dockerized deployment** – One-command setup via Docker Compose.
- **Async & concurrent** – Fully async I/O with `aiohttp` for handling multiple simultaneous users (up to 4 concurrent).
- **Robust error handling** – Graceful degradation, auto-reconnect, cascading health checks.

## Architecture

```
┌──────────┐     WebSocket      ┌──────────────────┐       HTTP        ┌─────────────────────────┐       HTTP        ┌──────────────┐       HTTP        ┌────────┐
│  Browser  │ ◄──────────────► │  Gateway Service  │ ◄──────────────►  │  Conversation Service   │ ◄──────────────► │  LLM Service  │ ◄──────────────► │ Ollama │
│  (Chat UI)│     :8000         │  (FastAPI + WS)   │     :8002         │  (Sessions + Prompts)   │     :8001         │  (Ollama Wrapper)│    :11434      │ (phi3) │
└──────────┘                    └──────────────────┘                    └─────────────────────────┘                    └──────────────┘                    └────────┘
```

**Why three services?**
- **Gateway Service** — Single entry point; handles WebSocket upgrades, serves frontend, can add auth/rate-limiting without touching business logic.
<<<<<<< HEAD
- **Conversation Service** — Owns session state, prompt templates, history management. Can evolve independently (e.g., swap to Redis-backed sessions).
=======
- **Conversation Service** — Owns prompt templates, history orchestration, and policy logic while persisting state in Redis.
>>>>>>> 32052ba (pushed the missing files)
- **LLM Service** — Thin wrapper around Ollama. Can be independently scaled or swapped for vLLM/llama.cpp without changing upstream services.

---

## Voice Interface (Assignment A3)

FitGuide AI now supports **voice-based interaction** powered by:

- **ASR (Speech-to-Text)** – OpenAI Whisper tiny model (local, CPU-friendly) ✅ **WORKING**
- **TTS (Text-to-Speech)** – pyttsx3 (system-integrated, no external APIs) ⚠️ **Linux/Docker needs eSpeak**

### Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| Voice recording | ✅ Working | MediaRecorder → WebM audio capture |
| Speech-to-text (ASR) | ✅ Working | Whisper tiny (39MB, CPU) with auto-resampling |
| Real-time chat | ✅ Working | Token-by-token WebSocket streaming |
| Text-to-speech (TTS) | ⚠️ Working (with setup) | Windows: ready. Linux/Docker: needs eSpeak. See [TTS Setup](#tts-setup-linuxdocker). |
| Stop button | ✅ Working | Pause/stop audio playback during response |

### How to Use Voice

1. Open http://localhost:8000
2. Click the **🎤 Voice** button
3. **Allow microphone access** in your browser
4. Speak clearly for 3-5 seconds
5. Click **⏹️ Stop** to submit
6. The transcribed text appears as a user message
7. The bot generates a response and **plays automatically** as audio (if TTS is initialized)

### Performance Benchmarks

| Component | Time | Technology |
|-----------|------|------------|
| Recording | 0-5s | User speaks |
| ASR (Whisper tiny) | 1-2s | 16kHz mono WAV on CPU |
| LLM Generation | 1-3s | Ollama + Phi3 |
| TTS (pyttsx3) | 0.5-2s | System text-to-speech |
| Network overhead | 0.5-1s | HTTP + WebSocket |
| **Total end-to-end** | **3-9s** | Depends on LLM response length |

**Optimizations Applied:**
- **Whisper tiny model** (39 MB instead of 140 MB) – ~2x faster ASR
- **CPU-only PyTorch** – Lighter dependencies, faster installs, no CUDA overhead
- **Result:** Docker builds ~50% faster, Docker image ~300MB smaller per service

**Note:** The assignment requirement is <1 second latency. This implementation prioritizes **functionality over latency** on CPU. To approach <1s:
- Enable GPU acceleration (if available) – Can reduce LLM inference by 10-50x
- Use even smaller LLM variant (e.g., Phi-3 mini, TinyLlama)
- Check [VOICE_SETUP_GUIDE.md](VOICE_SETUP_GUIDE.md) for detailed optimization notes

---

```
FitGuide-AI/
├── docker-compose.yml               # Orchestrates all 3 services
├── postman_collection.json           # Postman API test collection
├── requirements.txt                  # Root dependencies (monolith mode)
├── .dockerignore
├── Code/                             # Original monolith code (Phase I-III)
│   ├── main.py
│   ├── conversation_manager.py
│   ├── ollama_client.py
│   └── Frontend/
│       ├── index.html
│       ├── script.js
│       └── style.css
└── services/                         # Microservices (Phase IV)
    ├── llm_service/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── main.py                   # Wraps Ollama with streaming JSON API
    ├── conversation_service/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── main.py                   # Session mgmt & prompt orchestration
    └── gateway_service/
        ├── Dockerfile
        ├── requirements.txt
        ├── main.py                   # WebSocket gateway + static files
        └── frontend/
            ├── index.html
            ├── script.js
            └── style.css
```

---

## Prerequisites

- **Python 3.10+**
- **Ollama** installed and running locally with `phi3` model
- **Docker Desktop** (required for microservices / Phase IV deployment)

---

## Step 1 – Install Ollama

### Windows (PowerShell)

```powershell
irm https://ollama.com/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

After installation, verify Ollama is running:

```bash
ollama --version
```

---

## Step 2 – Download the Phi-3 Model

```bash
ollama run phi3
```

This downloads and loads the `phi3:latest` model. You can type a test message in the Ollama prompt to confirm it's working, then exit with `/bye`.

---

## Step 3 – Verify the Ollama API

Send a test request to make sure the API is accessible:

### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:11434/api/generate" `
  -Method Post `
  -Body '{"model":"phi3:latest","prompt":"Hello","stream":false}' `
  -ContentType "application/json"
```

### curl

```bash
curl http://localhost:11434/api/generate -d '{"model":"phi3:latest","prompt":"Hello","stream":false}'
```

A successful response will contain a `response` field with the model's reply.

---

## Step 4 – Set Up the Python Environment

> **Note:** Steps 4–6 describe running the original monolith code in `Code/`.
> For the **microservices deployment** (Phase IV), skip to [Docker Deployment](#docker-deployment-phase-iv--microservices) below.

### Create and activate a virtual environment

```bash
# Create
python -m venv ConversationalAI

# Activate (Windows PowerShell)
.\ConversationalAI\Scripts\Activate.ps1

# Activate (macOS / Linux)
source ConversationalAI/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 5 – Run the Application

Make sure Ollama is running in the background, then start the FastAPI server:

```bash
cd Code
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see output like:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

---

## Step 6 – Chat with FitGuide AI

1. Open your browser and navigate to **http://localhost:8000**
2. The FitGuide AI chat interface will load.
3. Type your message (e.g., *"I'm a beginner and want to build muscle"*) and click **Send**.
4. FitGuide AI will respond in real time with personalized fitness advice.
5. Click **New** to start a fresh conversation session.

### Example conversation

```
You:       Hi! I want to start working out but I'm a complete beginner.
FitGuide:  Welcome! I'd love to help you get started. Could you share your
           fitness goal (e.g., build muscle, lose weight, general fitness),
           your age, and current weight? Also, do you have any injuries I
           should know about?

You:       I'm 22, weigh 70 kg, and want to build muscle. No injuries.
FitGuide:  Great! Here's a 3-day beginner muscle-building plan...
```

## Troubleshooting

| Issue | Solution |
|---|---|
| `ConnectionError` when sending a message | Make sure Ollama is running (`ollama serve` or the Ollama app). |
| Model not found | Run `ollama pull phi3` to download the model. |
| Port 8000 already in use | Use a different port: `uvicorn main:app --port 8080` |
| WebSocket connection failed | Ensure you're accessing `http://localhost:8000`, not `https`. |
| Docker: `unable to get image` | Open Docker Desktop and wait for the engine to fully start. |
| Docker: `host.docker.internal` refused | Make sure Ollama is running on the host (`ollama serve`). |
| Docker: model memory error | Close other apps to free RAM; phi3 needs ~3.5 GB. |
| Docker: Gateway cannot reach LLM Service | Verify `docker compose.yml` has `LLM_SERVICE_URL` environment variable set to `http://llm_service:8001`. Services communicate by container name, not `localhost`. |
| Docker: `/synthesize` returns 500 | TTS (pyttsx3) requires eSpeak system library on Linux. See [TTS Setup (Linux/Docker)](#tts-setup-linuxdocker) below. |
| `docker` command not recognized | Install Docker Desktop and restart your terminal. |

### TTS Setup (Linux/Docker)

The text-to-speech feature using pyttsx3 requires the **eSpeak** system library. This is pre-installed on Windows but must be added to Docker Linux containers.

**For Docker Linux containers:**

The Dockerfile for the LLM service should include:

```dockerfile
RUN apt-get update && apt-get install -y espeak-ng && rm -rf /var/lib/apt/lists/*
```

If TTS is returning errors, rebuild the Docker image:

```bash
docker compose down
docker compose up --build
```

**For local Linux systems:**

```bash
# Ubuntu/Debian
sudo apt-get install espeak-ng

# macOS (Homebrew)
brew install espeak

# Fedora/RHEL
sudo dnf install espeak-ng
```

After installation, restart the LLM service.

---

## Docker Deployment (Phase IV — Microservices)

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Ollama** running on the host machine with `phi3` model downloaded

### Quick Start

```bash
# 1. Make sure Ollama is running
ollama serve

# 2. Build and start all services
docker compose up --build

# 3. Open the chat UI
# Navigate to http://localhost:8000
```

### What happens when you run `docker compose up`?

1. **Three containers** are built and started:
   - `fitguide-gateway` (port 8000) — serves the chat UI and WebSocket endpoint
   - `fitguide-conversation-service` (port 8002) — manages sessions and builds prompts
   - `fitguide-llm-service` (port 8001) — wraps Ollama's API
2. An internal Docker bridge network (`fitguide-network`) is created so services communicate by container name.
3. `host.docker.internal` is mapped to your host IP so the LLM service can reach Ollama running on the host.
4. Environment variables are set to enable inter-service communication (e.g., `LLM_SERVICE_URL=http://llm_service:8001` for the gateway).

### Service Health Checks

All services have health checks configured. Verify they're working:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "gateway": "ok",
  "downstream": {
    "status": "healthy",
    "llm_service": {
      "status": "healthy",
      "ollama": "connected",
      "model": "phi3:latest",
      "whisper": "loaded",
      "tts": "not initialized or initialized"
    }
  }
}
```

### Stopping

```bash
docker compose down
```

### Running Individual Services (without Docker)

**Recommended for development!** Run each service directly without containers.

#### Prerequisites

- Python 3.10+ installed and in PATH
- Ollama running in the background (`ollama serve`)

#### Setup Python Environment (First time only)

```powershell
# Navigate to the project root
cd path\to\FitGuide-AI

# Create a virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies for all services
pip install -r requirements.txt
cd services\llm_service && pip install -r requirements.txt
cd ..\conversation_service && pip install -r requirements.txt
cd ..\gateway_service && pip install -r requirements.txt
```

#### Quick Start (Windows PowerShell)

**Open 4 separate PowerShell terminals and run from the project root:**

**Terminal 1: Ollama (keep running)**
```powershell
ollama serve
```

**Terminal 2: LLM Service (port 8001)**
```powershell
cd services\llm_service
python main.py
```

**Terminal 3: Conversation Service (port 8002)**
```powershell
cd services\conversation_service
python main.py
```

**Terminal 4: Gateway Service (port 8000)**
```powershell
cd services\gateway_service
python main.py
```

Then open **http://localhost:8000** in your browser.

#### Quick Start (macOS / Linux Bash)

**Setup (one time):**
```bash
cd path/to/FitGuide-AI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd services/llm_service && pip install -r requirements.txt
cd ../conversation_service && pip install -r requirements.txt
cd ../gateway_service && pip install -r requirements.txt
```

**Running (open 4 terminals from project root):**

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: LLM Service
cd services/llm_service
python main.py

# Terminal 3: Conversation Service
cd services/conversation_service
python main.py

# Terminal 4: Gateway Service
cd services/gateway_service
python main.py
```

#### Troubleshooting

- **Port already in use?** Kill all Python: `taskkill /F /IM python.exe` (Windows) or `killall python` (macOS/Linux)
- **Module not found?** Ensure environment is activated: `source venv/bin/activate` (macOS/Linux) or `.\venv\Scripts\Activate.ps1` (Windows)
- **Python not found?** Install Python 3.10+ from [python.org](https://www.python.org). Ensure "Add to PATH" is checked during installation.
- **Ollama not found?** Install from [ollama.ai](https://ollama.ai)

---

## API Endpoints

### Gateway Service (port 8000)

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the chat UI |
| `/ws/chat` | WebSocket | Real-time chat (send JSON, receive streaming tokens) |
| `/health` | GET | Cascading health check (all services) |
| `/connections` | GET | Number of active WebSocket connections |
| `/transcribe` | POST | Audio transcription proxy (forwards to LLM service) |
| `/synthesize` | POST | Text-to-speech proxy (forwards to LLM service) |

### Conversation Service (port 8002)

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Send a chat message (streaming NDJSON response) |
| `/session/{id}` | GET | Get session info |
| `/session/{id}` | DELETE | Delete a session |
| `/health` | GET | Health check |

### LLM Service (port 8001)

| Endpoint | Method | Description |
|---|---|---|
| `/generate` | POST | Generate tokens (streaming NDJSON response) |
| `/health` | GET | Health check + Ollama connectivity |
| `/transcribe` | POST | Transcribe audio to text (Whisper ASR) |
| `/synthesize` | POST | Synthesize text to speech (pyttsx3 TTS) |

### WebSocket Protocol

```
Client → Server:  {"session_id": "abc123", "message": "Hello!"}
Server → Client:  "Hello"  (token)
Server → Client:  "!"      (token)
Server → Client:  " How"   (token)
...
Server → Client:  "[END]"  (signals response complete)
```

---

## Postman Testing

Import `postman_collection.json` into Postman to test all endpoints:

1. **Health Checks** — Verify all 3 services are running and connected
2. **Chat** — Send messages directly to the conversation service
3. **Session Management** — Get/delete sessions
4. **LLM Direct** — Test token generation directly
5. **WebSocket** — Connect to `ws://localhost:8000/ws/chat` in Postman's WebSocket tab

---

## Performance & Design Decisions

- **Async everywhere**: All HTTP calls between services use `aiohttp` (non-blocking). The event loop is never blocked, so the server handles many concurrent WebSocket users.
- **Streaming end-to-end**: Tokens stream from Ollama → LLM Service → Conversation Service → Gateway → Browser. No buffering — first-token latency is as low as Ollama allows.
<<<<<<< HEAD
- **Sliding window history**: Only the last 8 messages are kept per session to fit within small model context windows (~4K tokens for phi3).
- **Graceful degradation**: Health checks cascade through all services. Frontend auto-reconnects on WebSocket drops with exponential backoff.
- **Stateless-friendly**: Session state is in-memory but isolated to the conversation service. Swapping to Redis requires changes in only one service.
=======
- **Sliding window history**: Only the last 6 messages are kept verbatim per session to fit small-model context windows.
- **Graceful degradation**: Health checks cascade through all services. Frontend auto-reconnects on WebSocket drops with exponential backoff.
- **Stateless backend**: Session/profile/memory and benchmark state are persisted in Redis, so service restarts do not lose conversation state.
>>>>>>> 32052ba (pushed the missing files)

---

## Assignment A3 Requirements Compliance

### ✅ Implemented Requirements

- **[PASS] Voice Interface** – ASR (Whisper) + TTS (pyttsx3) with web UI integration
- **[PASS] Local Deployment** – All models local (Ollama, Whisper, pyttsx3); no cloud APIs
- **[PASS] Conversational AI** – Multi-turn dialogue with session state management
- **[PASS] Microservices Architecture** – 3 independent services (Gateway, Conversation, LLM) orchestrated via Docker Compose
- **[PASS] Concurrent Users** – Async aiohttp + WebSocket multiplexing supports 4+ concurrent users
- **[PASS] Prompt Orchestration** – System prompt + user profile + conversation history (no Tools/RAG)
- **[PASS] ChatGPT-style UI** – Web interface with chat box and voice button
- **[PASS] Docker Deployment** – Fully containerized with health checks and networking

### ⚠️ Performance Note

- **Latency Requirement:** < 1 second (assignment requirement)
- **Current Performance:** 4-16 seconds (cpu-only)
- **Status:** Does NOT meet <1s requirement on CPU
- **Trade-off:** Implementation prioritizes functionality and code clarity over latency optimization

**To improve latency:**
1. Use GPU acceleration (if available) – Can reduce LLM inference by 10-50x
2. Switch to smaller, quantized LLM variant (e.g., Phi-3 mini, TinyLlama)
3. Use faster Whisper variant (tiny or small vs. base)
4. Enable streaming TTS (start audio before synthesis completes)

For assignment context, see [VOICE_SETUP_GUIDE.md](VOICE_SETUP_GUIDE.md) for full benchmark breakdown and optimization strategies.

---

## Known Limitations

<<<<<<< HEAD
- Session data is in-memory (lost on container restart). Production would use Redis.
=======
- Redis must be running and reachable by the conversation service.
>>>>>>> 32052ba (pushed the missing files)
- No authentication or rate limiting (would be added to the gateway in production).
- Ollama must run on the host — not containerized — for direct CPU/GPU access.
- Context window is limited to 8 messages due to small model constraints.
- Latency is 3-9 seconds on CPU (not meeting <1s assignment goal); GPU or model optimization required.
- **TTS (Text-to-Speech) on Linux/Docker:** pyttsx3 requires eSpeak system library. Windows has built-in support; Linux containers need eSpeak installed. See [TTS Setup (Linux/Docker)](#tts-setup-linuxdocker).
- **Voice ASR (Speech-to-Text):** Works on all platforms. Latency is 1-2s for Whisper tiny model on CPU.
