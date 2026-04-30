# FitGuide AI - Quick Start Guide

## 🎯 Current Status

✅ **Merge conflicts resolved** (except 1 file - see below)
✅ **Redis integration** for session persistence  
✅ **Voice features** (ASR + TTS)  
✅ **Microservices architecture** ready  
⚠️ **One file needs restoration** before running

---

## 🚨 CRITICAL: Restore Missing File

Before running the project, restore the conversation service:

```bash
cd FitGuide-AI
git checkout 32052ba -- services/conversation_service/main.py
```

**If the above doesn't work**, you have two options:
1. Use `git log` to find the correct commit hash and replace `32052ba`
2. Ask me to help recreate the file from scratch

---

## 📋 Prerequisites

1. **Docker Desktop** - Running and ready
2. **Ollama** - Installed with phi3 model
3. **Git** - For version control

### Install Ollama & Phi-3

```bash
# Install Ollama (Windows PowerShell)
irm https://ollama.com/install.ps1 | iex

# Or macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Download Phi-3 model
ollama run phi3
# Type /bye to exit after it loads
```

---

## 🚀 Running the Project

### Step 1: Start Ollama

```bash
ollama serve
```

Keep this terminal open.

### Step 2: Start All Services

Open a new terminal:

```bash
cd FitGuide-AI
docker compose up --build
```

This starts:
- Redis (port 6379)
- LLM Service (port 8001)
- Conversation Service (port 8002)
- Gateway Service (port 8000)

### Step 3: Access the Application

Open your browser:
```
http://localhost:8000
```

---

## ✅ Verify Everything Works

### 1. Health Check

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

### 2. Test Chat

1. Open http://localhost:8000
2. Type: "I'm 25, weigh 75kg, want to build muscle"
3. Bot should respond with a personalized plan

### 3. Test Voice

1. Click 🎤 **Voice** button
2. Allow microphone access
3. Speak: "Give me a chest workout"
4. Click ⏹️ **Stop**
5. Verify transcription and audio response

### 4. Test Session Persistence

1. Chat with the bot
2. Stop services: `docker compose down`
3. Restart: `docker compose up`
4. Continue chatting - your profile should be remembered!

---

## 🛠️ Troubleshooting

### "Cannot reach Ollama"
```bash
# Verify Ollama is running
ollama serve

# Test API
curl http://localhost:11434/api/tags
```

### "Redis connection failed"
```bash
# Check Redis container
docker ps | grep redis

# Restart Redis
docker restart fitguide-redis
```

### "Port already in use"
```bash
# Windows - find what's using the port
netstat -ano | findstr "8000"

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

### Voice not working
- Check browser console (F12) for errors
- Ensure microphone permissions granted
- Check LLM service logs: `docker logs fitguide-llm-service`

---

## 📊 System Architecture

```
Browser (http://localhost:8000)
    ↓ WebSocket
Gateway Service (:8000)
    ↓ HTTP
Conversation Service (:8002) ←→ Redis (:6379)
    ↓ HTTP
LLM Service (:8001)
    ↓ HTTP
Ollama (:11434) - Phi-3 Model
```

---

## 🎓 Ready for Assignment A4

Once the system is running, you're ready to add:

### 1. RAG (Retrieval-Augmented Generation)
- 100-150 fitness documents
- Vector database (Chroma/FAISS)
- Embedding model (sentence-transformers)
- Document retrieval pipeline

### 2. CRM Tool
- User profile management
- Store/retrieve/update operations
- LLM-callable tool interface

### 3. Additional Tools
- **Nutrition Calculator** - Calorie/macro calculations
- **Exercise Database** - Exercise lookup and recommendations
- **Workout Scheduler** - Schedule and track workouts
- **(Optional) 4th tool** - Your choice!

---

## 📚 Useful Commands

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker logs -f fitguide-gateway
docker logs -f fitguide-conversation-service
docker logs -f fitguide-llm-service
docker logs -f fitguide-redis

# Restart a service
docker restart fitguide-gateway

# Stop everything
docker compose down

# Stop and remove volumes (clears Redis data)
docker compose down -v

# Rebuild a specific service
docker compose up --build gateway_service

# Check Redis data
docker exec -it fitguide-redis redis-cli
# Then: KEYS *
# Then: GET fitguide:session:<session_id>
```

---

## 📖 Additional Documentation

- **SETUP_GUIDE.md** - Detailed setup instructions
- **MERGE_CONFLICTS_RESOLVED.md** - What was fixed
- **README.md** - Full project documentation
- **VOICE_SETUP_GUIDE.md** - Voice feature details

---

## 🆘 Need Help?

1. Check the logs: `docker compose logs -f`
2. Verify prerequisites are installed
3. Ensure ports 8000, 8001, 8002, 6379, 11434 are available
4. Try rebuilding: `docker compose up --build`
5. Check health endpoint: `curl http://localhost:8000/health`

---

## ✨ Next Steps

1. ✅ Restore conversation_service/main.py
2. ✅ Verify system runs
3. ✅ Test all features
4. 🚀 Start building A4 features!

**Good luck with Assignment A4!** 🎉
