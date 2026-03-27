# FitGuide AI Voice - Complete Setup & Testing Guide

## 🎉 Status: READY TO USE

### ✅ All Services Running
- **Gateway Service** (port 8000): http://localhost:8000 ✓
- **Conversation Service** (port 8002): Internal ✓  
- **LLM Service** (port 8001): Internal + Voice ✓

### ✅ Voice Features
- **ASR** (Speech → Text): Whisper (OpenAI) on CPU
- **TTS** (Text → Speech): pyttsx3 (system voice)
- **API Access**: Through Gateway proxy endpoints (no CORS issues)

---

## 🔧 Getting Started

### Step 1: Open Browser
```
http://localhost:8000
```

### Step 2: Click Voice Button
You'll see:
- 🎤 **Voice** button (green)
- Text input field
- Chat display

### Step 3: Record Your Message
1. Click **🎤 Voice** button
2. Button turns **red with pulsing animation** (recording)
3. **Allow microphone access** when browser asks
4. Speak clearly (3-5 seconds)
5. Click **⏹️ Stop** button

### Step 4: Wait for Processing

Browser console shows progression:
```
[Voice] Recording complete. Format: wav, Size: 45.23KB
[Voice] Sending to: /transcribe
[Voice] Transcribe response: 200 OK
[Voice] Transcription success: {text: "How do I build muscle?"}
```

### Step 5: See Response
1. **Transcribed text** appears as user message
2. AI thinks (1-3 seconds)
3. **Bot response** in chat
4. **Audio plays automatically** 🔊

---

## 🔍 What Happens Behind the Scenes

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (localhost:8000)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ User clicks 🎤 Voice → Records audio as WAV         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────┬──────────────────────┘
                                      │
                         POST /transcribe (local)
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│          GATEWAY SERVICE (localhost:8000)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Receives WAV file                                    │  │
│  │ Forwards to LLM Service /transcribe                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────┬──────────────────────┘
                                      │
                    Internal HTTP call (no CORS)
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│           LLM SERVICE (localhost:8001)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Whisper ASR: Transcribes WAV → Text                 │  │
│  │ Returns: {"text": "How do I build muscle?"}         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────┬──────────────────────┘
                                      │
                        Returns JSON to Gateway
                                      │
                                      ▼
                  Browser displays transcribed text
                                      │
                  User message sent via WebSocket
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│       CONVERSATION SERVICE (localhost:8002)                 │
│  Manages conversation state → Sends to LLM                 │
│       Returns response via WebSocket streaming             │
└─────────────────────────────────────┬──────────────────────┘
                                      │
                      Bot response received in browser
                                      │
                                      ▼
                        POST /synthesize (local)
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│           LLM SERVICE (localhost:8001)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ pyttsx3 TTS: Converts response → MP3 audio          │  │
│  │ Returns: audio/mpeg binary data                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────┬──────────────────────┘
                                      │
                      Returns MP3 to Gateway
                                      │
                                      ▼
      Browser receives audio, plays automatically via
              <audio> element in HTML
                                      │
                                      ▼
                          🔊 USER HEARS RESPONSE
```

---

## ⏱️ Performance Benchmarks

| Component | Time |  Technology |
|-----------|------|------------|
| Recording | 0-5s | User speaks |
| ASR (Whisper base) | 2-5s | 16kHz mono WAV |
| LLM Generation | 1-3s | Ollama + Phi3 |
| TTS (pyttsx3) | 0.5-2s | System voice |
| Network + Overhead | 0.5-1s | HTTP calls |
| **Total Round Trip** | **4-16s** | Depends on LLM |

**Note:** Assignment requires <1s latency. This implementation prioritizes **functionality over latency**. For optimization, consider:
- Using quantized LLM (faster inference)
- Streaming TTS (start audio before synthesis completes)
- GPU acceleration (if available)

---

## 🐛 Troubleshooting

### Issue: "Transcription failed" in chat

**Cause**: Network error or LLM service not responding

**Fix**:
1. Open browser **Console** (F12)
2. Look for `[Voice]` prefixed messages
3. Check that all 3 ports are open: `netstat -an | find ":800"`
4. Verify Ollama is running: `ollama serve`

### Issue: Hear nothing after response

**Possible causes**:

1. **Browser volume muted** → Check OS volume
2. **No audio device** → Check system speakers
3. **TTS failed** → Check LLM service logs
4. **Different browser** → Try Chrome/Edge/Firefox

### Issue: Microphone not working

**Fix**:
1. Browser security: Click 🔒 in address bar
2. Allow "Microphone: Allow"
3. Refresh page
4. Try again

### Issue: Server errors (5xx)

**Debug**:
```powershell
# Check service logs
Get-Process python

# Restart LLM service
Kill service, then: python -m uvicorn main:app --port 8001

# Check for errors
pip install -r requirements.txt
```

---

## 📝 Key Changes From Initial Setup

### ✅ Fixed Issues

1. **FFmpeg Dependency** ✓
   - Removed Coqui TTS (had complicated dependencies)
   - Switched to pyttsx3 (system TTS, no downloads)

2. **CORS Errors** ✓
   - Added voice proxy endpoints to Gateway Service
   - Frontend now uses `/transcribe` and `/synthesize` (same origin)
   - No more cross-origin request issues

3. **WAV Format Support** ✓
   - Updated frontend to prefer WAV (native browser support)
   - Backend loads WAV with scipy (no FFmpeg needed)
   - Fallback to WebM if WAV not supported

4. **Error Handling** ✓
   - Better console logging with `[Voice]` prefix
   - Detailed error messages in chat
   - Health checks on page load

---

## 🚀 Production Deployment Notes

### Docker Compose
```bash
docker-compose up -d
```
- Automatically handles internal networking
- No port conflicts
- Isolated environments

### Environment Variables Needed
- `CONVERSATION_SERVICE_URL=http://conversation_service:8002`
- `LLM_SERVICE_URL=http://llm_service:8001`
- `OLLAMA_URL=http://host.docker.internal:11434` (Windows/Mac)

### Security
- Add authentication layer in gateway
- Validate file uploads (max size, format)
- Rate limit voice requests
- Sanitize text inputs

---

## 📚 Code Structure

```
FitGuide-AI/
├── services/
│   ├── gateway_service/
│   │   ├── main.py (NEW: /transcribe, /synthesize proxies)
│   │   └── frontend/
│   │       ├── index.html (NEW: voice button, audio element)
│   │       ├── script.js (NEW: recording, transcription, playback)
│   │       └── style.css (NEW: voice button styling)
│   ├── llm_service/
│   │   ├── main.py (NEW: /transcribe, /synthesize endpoints)
│   │   └── requirements.txt (pyttsx3, whisper, scipy)
│   ├── conversation_service/
│   │   └── main.py (unchanged, handles conversation logic)
│
├── START_SERVICES.bat (quick launch script)
└── docker-compose.yml (unchanged)
```

---

## ✨ Next Feature Ideas

1. **Streaming TTS** - Start audio before synthesis completes
2. **Voice Commands** - "Next question", "Clear chat", etc.
3. **Multiple Voices** - Select different TTS voices
4. **Conversation History Download** - Export chat as PDF
5. **Language Support** - Multi-language ASR/TTS
6. **Real-time Visualizer** - Show audio waveform while recording
7. **Microphone Test** - Record sample before chat

---

**Ready to demo?** 🎤 Open http://localhost:8000 and click 🎤 Voice!
