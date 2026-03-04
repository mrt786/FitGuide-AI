# FitGuide AI – Gym Coaching Assistant

FitGuide AI is a conversational gym coaching assistant powered by a local LLM (Phi-3) via Ollama. It provides personalized workout plans, motivational support, and fitness guidance through a real-time chat interface built with FastAPI WebSockets.

## Features

- **Real-time streaming chat** – Responses are streamed token-by-token over WebSockets for a smooth experience.
- **Session management** – Each connection gets a unique session with conversation history and user profile tracking.
- **User profiling** – Tracks fitness goal, experience level, age, weight, and injury status to personalize advice.
- **Local & private** – Runs entirely on your machine using Ollama; no data leaves your system.

## Project Structure

```
Code/
├── main.py                  # FastAPI app with WebSocket endpoint
├── conversation_manager.py  # Session, history & prompt management
├── ollama_client.py         # Streams responses from Ollama API
└── Frontend/
    ├── index.html           # Chat UI
    ├── script.js            # WebSocket client logic
    └── style.css            # Styling
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
