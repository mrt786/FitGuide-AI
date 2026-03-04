# FitGuide AI – Gym Coaching Assistant

FitGuide AI is a conversational gym coaching assistant powered by a local LLM (Phi-3) via Ollama. It provides personalized workout plans, motivational support, and fitness guidance through a real-time chat interface built with FastAPI WebSockets.

## Features

- **Real-time streaming chat** – Responses are streamed token-by-token over WebSockets for a smooth experience.
- **Session management** – Each connection gets a unique session with conversation history and user profile tracking.
- **User profiling** – Tracks fitness goal, experience level, age, weight, and injury status to personalize advice.
- **Local & private** – Runs entirely on your machine using Ollama; no data leaves your system.
- **Microservices architecture** – Three independent containerized services communicating over HTTP.
- **Dockerized deployment** – One-command setup via Docker Compose.
- **Async & concurrent** – Fully async I/O with `aiohttp` for handling multiple simultaneous users.
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
- **Conversation Service** — Owns session state, prompt templates, history management. Can evolve independently (e.g., swap to Redis-backed sessions).
- **LLM Service** — Thin wrapper around Ollama. Can be independently scaled or swapped for vLLM/llama.cpp without changing upstream services.

## Project Structure

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
- **Ollama** installed and running locally
- (Optional) **Docker** if you prefer containerized deployment

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
| Model not found | Run `ollama run phi3` to download the model. |
| Port 8000 already in use | Use a different port: `uvicorn main:app --port 8080` |
| WebSocket connection failed | Ensure you're accessing `http://localhost:8000`, not `https`. |

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

### Stopping

```bash
docker compose down
```

### Running Individual Services (without Docker)

You can also run each service directly for development:

```bash
# Terminal 1: LLM Service
cd services/llm_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Conversation Service
cd services/conversation_service
pip install -r requirements.txt
LLM_SERVICE_URL=http://localhost:8001 uvicorn main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 3: Gateway Service
cd services/gateway_service
pip install -r requirements.txt
CONVERSATION_SERVICE_URL=http://localhost:8002 uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Endpoints

### Gateway Service (port 8000)

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the chat UI |
| `/ws/chat` | WebSocket | Real-time chat (send JSON, receive streaming tokens) |
| `/health` | GET | Cascading health check (all services) |
| `/connections` | GET | Number of active WebSocket connections |

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
- **Sliding window history**: Only the last 8 messages are kept per session to fit within small model context windows (~4K tokens for phi3).
- **Graceful degradation**: Health checks cascade through all services. Frontend auto-reconnects on WebSocket drops with exponential backoff.
- **Stateless-friendly**: Session state is in-memory but isolated to the conversation service. Swapping to Redis requires changes in only one service.

---

## Known Limitations

- Session data is in-memory (lost on container restart). Production would use Redis.
- No authentication or rate limiting (would be added to the gateway in production).
- Ollama must run on the host — not containerized — for direct CPU/GPU access.
- Context window is limited to 8 messages due to small model constraints.
