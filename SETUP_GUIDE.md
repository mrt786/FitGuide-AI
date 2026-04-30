# FitGuide AI - Complete Setup Guide

## ✅ Merge Conflicts Resolved

All Git merge conflicts have been resolved. The project now uses the newer branch with:
- Redis-backed session persistence
- Better health checks
- Improved concurrency handling
- Profile extraction features

---

## Prerequisites

Before running the project, ensure you have:

1. **Docker Desktop** installed and running
2. **Ollama** installed on your host machine
3. **Phi-3 model** downloaded in Ollama
4. **Git** (to clone/manage the repository)

---

## Step-by-Step Setup Instructions

### 1. Install Ollama

#### Windows (PowerShell)
```powershell
irm https://ollama.com/install.ps1 | iex
```

#### macOS / Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

Verify installation:
```bash
ollama --version
```

### 2. Download the Phi-3 Model

```bash
ollama run phi3
```

This downloads and loads the `phi3:latest` model. Type `/bye` to exit after it loads.

### 3. Verify Ollama API

Test that Ollama is accessible:

#### PowerShell
```powershell
Invoke-RestMethod -Uri "http://localhost:11434/api/generate" `
  -Method Post `
  -Body '{"model":"phi3:latest","prompt":"Hello","stream":false}' `
  -ContentType "application/json"
```

#### curl (macOS/Linux)
```bash
curl http://localhost:11434/api/generate -d '{"model":"phi3:latest","prompt":"Hello","stream":false"}'
```

You should see a JSON response with the model's reply.

---

## Running the Project

### Option 1: Docker Compose (Recommended)

This runs all services in containers with Redis for state persistence.

#### Step 1: Ensure Ollama is Running

```bash
# Check if Ollama is running
ollama serve
```

Keep this terminal open or run Ollama as a background service.

#### Step 2: Build and Start All Services

Navigate to the FitGuide-AI directory:

```bash
cd FitGuide-AI
```

Build and start all containers:

```bash
docker compose up --build
```

This will:
- Start Redis (port 6379)
- Build and start LLM Service (port 8001)
- Build and start Conversation Service (port 8002)
- Build and start Gateway Service (port 8000)

#### Step 3: Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

You should see the FitGuide AI chat interface!

#### Step 4: Test Voice Features

1. Click the **🎤 Voice** button
2. Allow microphone access when prompted
3. Speak for 3-5 seconds
4. Click **⏹️ Stop** to submit
5. The transcribed text will appear and the bot will respond with audio

#### Stopping the Services

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (clears Redis data)
docker compose down -v
```

---

### Option 2: Run Services Locally (Development)

For development, you can run each service directly without Docker.

#### Prerequisites
- Python 3.10+ installed
- Virtual environment created

#### Setup (One-time)

```bash
# Navigate to project root
cd FitGuide-AI

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies for all services
pip install -r requirements.txt
cd services/llm_service && pip install -r requirements.txt
cd ../conversation_service && pip install -r requirements.txt
cd ../gateway_service && pip install -r requirements.txt
cd ../..
```

#### Running (Open 5 terminals)

**Terminal 1: Ollama**
```bash
ollama serve
```

**Terminal 2: Redis**
```bash
# Install Redis if not already installed
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# macOS: brew install redis
# Linux: sudo apt-get install redis-server

redis-server
```

**Terminal 3: LLM Service**
```bash
cd FitGuide-AI/services/llm_service
python main.py
```

**Terminal 4: Conversation Service**
```bash
cd FitGuide-AI/services/conversation_service
python main.py
```

**Terminal 5: Gateway Service**
```bash
cd FitGuide-AI/services/gateway_service
python main.py
```

Then open **http://localhost:8000** in your browser.

---

## Health Checks

### Check All Services

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
    "redis": "connected",
    "llm_service": {
      "status": "healthy",
      "ollama": "connected",
      "model": "phi3:latest",
      "whisper": "loaded",
      "tts": "initialized"
    }
  }
}
```

### Check Individual Services

```bash
# Gateway
curl http://localhost:8000/health

# Conversation Service
curl http://localhost:8002/health

# LLM Service
curl http://localhost:8001/health
```

---

## Architecture Overview

```
┌──────────┐     WebSocket      ┌──────────────────┐       HTTP        ┌─────────────────────────┐       HTTP        ┌──────────────┐       HTTP        ┌────────┐
│  Browser  │ ◄──────────────► │  Gateway Service  │ ◄──────────────►  │  Conversation Service   │ ◄──────────────► │  LLM Service  │ ◄──────────────► │ Ollama │
│  (Chat UI)│     :8000         │  (FastAPI + WS)   │     :8002         │  (Sessions + Prompts)   │     :8001         │  (Ollama Wrapper)│    :11434      │ (phi3) │
└──────────┘                    └──────────────────┘                    └─────────────────────────┘                    └──────────────┘                    └────────┘
                                                                                    │
                                                                                    ▼
                                                                            ┌──────────────┐
                                                                            │    Redis     │
                                                                            │ (State Store)│
                                                                            └──────────────┘
```

### Service Responsibilities

| Service | Port | Purpose |
|---------|------|---------|
| **Gateway** | 8000 | WebSocket endpoint, serves frontend, voice proxy |
| **Conversation** | 8002 | Session management, prompt orchestration, Redis state |
| **LLM** | 8001 | Ollama wrapper, Whisper ASR, pyttsx3 TTS |
| **Redis** | 6379 | Session persistence, metrics storage |
| **Ollama** | 11434 | LLM inference (Phi-3 model) |

---

## Troubleshooting

### Issue: Docker containers won't start

**Solution:**
1. Ensure Docker Desktop is running
2. Check if ports 8000, 8001, 8002, 6379 are available:
   ```bash
   # Windows
   netstat -an | findstr "8000 8001 8002 6379"
   # macOS/Linux
   lsof -i :8000,8001,8002,6379
   ```
3. Stop any conflicting services

### Issue: "Cannot reach Ollama"

**Solution:**
1. Verify Ollama is running: `ollama serve`
2. Test Ollama API: `curl http://localhost:11434/api/tags`
3. Ensure phi3 model is downloaded: `ollama list`

### Issue: Redis connection failed

**Solution:**
1. Check if Redis container is running: `docker ps | grep redis`
2. Check Redis logs: `docker logs fitguide-redis`
3. Restart Redis: `docker restart fitguide-redis`

### Issue: Voice transcription fails

**Solution:**
1. Check browser console for errors (F12)
2. Ensure microphone permissions are granted
3. Check LLM service logs: `docker logs fitguide-llm-service`
4. Verify Whisper model loaded in health check

### Issue: TTS (Text-to-Speech) not working

**Solution:**
1. **Linux/Docker**: Ensure eSpeak is installed in the container (already in Dockerfile)
2. **Windows**: Should work out of the box with system TTS
3. Check LLM service logs for TTS initialization errors
4. Rebuild containers: `docker compose up --build`

### Issue: "Response still generating" error

**Solution:**
- This is normal - wait for the current response to complete
- If stuck, click "New" to reset the session
- Check conversation service logs for errors

---

## Testing the System

### 1. Basic Chat Test

1. Open http://localhost:8000
2. Type: "I'm 25 years old, weigh 75kg, and want to build muscle"
3. Verify the bot responds with a personalized plan
4. Type: "What's my goal?" - it should remember "build muscle"

### 2. Voice Test

1. Click 🎤 Voice button
2. Say: "Give me a chest workout"
3. Click ⏹️ Stop
4. Verify transcription appears
5. Verify bot responds with audio

### 3. Session Persistence Test

1. Chat with the bot and provide profile info
2. Stop all services: `docker compose down`
3. Restart services: `docker compose up`
4. Continue the conversation - your profile should be remembered (thanks to Redis!)

### 4. Concurrent Users Test

1. Open http://localhost:8000 in two different browsers
2. Chat simultaneously in both
3. Verify both sessions work independently

---

## Next Steps (Assignment A4)

Now that the base system is working, you're ready to add:

1. **RAG (Retrieval-Augmented Generation)** - 100-150 fitness documents
2. **CRM Tool** - User profile management
3. **Nutrition Calculator Tool** - Calorie/macro calculations
4. **Exercise Database Tool** - Exercise lookup and recommendations
5. **Workout Scheduler Tool** - Schedule and track workouts

See the main assignment document for detailed requirements.

---

## Useful Commands

```bash
# View logs for all services
docker compose logs -f

# View logs for specific service
docker logs -f fitguide-gateway
docker logs -f fitguide-conversation-service
docker logs -f fitguide-llm-service
docker logs -f fitguide-redis

# Restart a specific service
docker restart fitguide-gateway

# Rebuild a specific service
docker compose up --build gateway_service

# Check running containers
docker ps

# Check Redis data
docker exec -it fitguide-redis redis-cli
# Then: KEYS *
# Then: GET fitguide:session:<session_id>

# Clean up everything (including volumes)
docker compose down -v
docker system prune -a
```

---

## Performance Benchmarks

Current system performance (CPU-only):

| Component | Latency |
|-----------|---------|
| ASR (Whisper tiny) | 1-2s |
| LLM Generation | 1-3s |
| TTS (pyttsx3) | 0.5-2s |
| **Total End-to-End** | **4-16s** |

**Note:** This does not meet the <1s requirement but prioritizes functionality. GPU acceleration would significantly improve latency.

---

## Support

If you encounter issues:

1. Check the logs: `docker compose logs -f`
2. Verify all prerequisites are installed
3. Ensure ports are not in use
4. Try rebuilding: `docker compose up --build`
5. Check the README.md for additional troubleshooting

---

**Ready to start building Assignment A4 features!** 🚀
