/**
 * FitGuide AI — Frontend WebSocket Client with Voice Support
 *
 * Key change for microservices: The WebSocket URL is now derived from
 * the current page URL (window.location) instead of being hardcoded.
 * This means the frontend works regardless of whether the server runs
 * on localhost:8000, a Docker container, or a deployed domain.
 *
 * Voice features:
 * - Record audio input using Web Audio API
 * - Send to /transcribe endpoint for ASR
 * - Receive synthesized audio from /synthesize endpoint
 * - Play audio responses
 */

let sessionId = generateSessionId();
let ws = null;
let currentBotMessage = null;
let currentBotMessageTtsTriggered = false;  // Track if TTS already triggered for this response
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
<<<<<<< HEAD
=======
let responseInProgress = false;
>>>>>>> 32052ba (pushed the missing files)

// Voice recording state
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioContext = null;  // Will be created on first recording
// Use gateway endpoints (same origin, no CORS needed)
// Voice endpoints are proxied through /transcribe and /synthesize on same server
const VOICE_API_URL = ""; // Empty = use current origin

function generateSessionId() {
    return Math.random().toString(36).substring(2);
}

function getWebSocketUrl() {
    // Derive WS URL from the current page location — works everywhere.
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws/chat`;
}

function connectWebSocket() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return ws;
    }

    const url = getWebSocketUrl();
    console.log("Connecting to WebSocket:", url);
    const socket = new WebSocket(url);

    socket.onopen = function () {
        console.log("WebSocket connected");
        reconnectAttempts = 0;
    };

    socket.onmessage = function (event) {
        if (event.data === "[END]") {
            hideTyping();
<<<<<<< HEAD
=======
            setChatControlsDisabled(false);
            responseInProgress = false;
>>>>>>> 32052ba (pushed the missing files)
            // Generate audio for complete response (Option 3)
            if (currentBotMessage && currentBotMessage.textContent.trim().length > 0) {
                console.log("[TTS] Response complete [END], generating full audio...");
                playResponse(currentBotMessage.textContent);
            }
            currentBotMessage = null;
            currentBotMessageTtsTriggered = false;
            return;
        }

        // Handle error messages from the gateway
        if (event.data.startsWith("[ERROR]")) {
            hideTyping();
<<<<<<< HEAD
=======
            setChatControlsDisabled(false);
            responseInProgress = false;
>>>>>>> 32052ba (pushed the missing files)
            if (!currentBotMessage) {
                currentBotMessage = appendMessage("", "bot");
            }
            currentBotMessage.textContent = "⚠️ " + event.data.replace("[ERROR] ", "");
            currentBotMessage.style.color = "#dc2626";
            currentBotMessage = null;
            currentBotMessageTtsTriggered = false;
            return;
        }

        if (!currentBotMessage) {
            currentBotMessage = appendMessage("", "bot");
        }

        currentBotMessage.textContent += event.data;
        scrollToBottom();
    };

    socket.onclose = function (event) {
        console.log("WebSocket closed:", event.code, event.reason);
<<<<<<< HEAD
=======
        if (!responseInProgress) {
            setChatControlsDisabled(false);
        }
>>>>>>> 32052ba (pushed the missing files)
        // Auto-reconnect with exponential backoff
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
            console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})...`);
            setTimeout(() => {
                ws = connectWebSocket();
            }, delay);
        }
    };

    socket.onerror = function (error) {
        console.error("WebSocket error:", error);
    };

    return socket;
}

// Initialize connection
ws = connectWebSocket();

function sendMessage() {
    const input = document.getElementById("message-input");
    const message = input.value.trim();
<<<<<<< HEAD
    if (!message) return;
=======
    if (!message || responseInProgress) return;
>>>>>>> 32052ba (pushed the missing files)

    // Reconnect if needed
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        ws = connectWebSocket();
        // Wait for connection then retry
        setTimeout(() => sendMessage(), 500);
        return;
    }

    appendMessage(message, "user");
    showTyping();
<<<<<<< HEAD
=======
    responseInProgress = true;
    setChatControlsDisabled(true);
>>>>>>> 32052ba (pushed the missing files)

    ws.send(JSON.stringify({
        session_id: sessionId,
        message: message
    }));

    input.value = "";
}

<<<<<<< HEAD
=======
function setChatControlsDisabled(disabled) {
    const input = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-btn");
    const voiceBtn = document.getElementById("voice-btn");
    const newBtn = document.getElementById("new-btn");

    input.disabled = disabled;
    sendBtn.disabled = disabled;
    voiceBtn.disabled = disabled;
    if (newBtn) {
        newBtn.disabled = false;
    }
}

>>>>>>> 32052ba (pushed the missing files)
function appendMessage(text, sender) {
    const chatBox = document.getElementById("chat-box");

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender);
    messageDiv.textContent = text;

    chatBox.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

function scrollToBottom() {
    const chatBox = document.getElementById("chat-box");
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping() {
    document.getElementById("typing-indicator").style.display = "block";
}

function hideTyping() {
    document.getElementById("typing-indicator").style.display = "none";
}

function resetSession() {
    sessionId = generateSessionId();
    document.getElementById("chat-box").innerHTML = "";
    currentBotMessage = null;
<<<<<<< HEAD
=======
    responseInProgress = false;
    setChatControlsDisabled(false);
>>>>>>> 32052ba (pushed the missing files)
    // Reconnect WebSocket for clean state
    if (ws) ws.close();
    ws = connectWebSocket();
}

/* ──────────────────────────────────────────────────────────────────
   VOICE FUNCTIONS — Recording & Playback
   ────────────────────────────────────────────────────────────────── */

async function toggleVoiceRecording() {
<<<<<<< HEAD
=======
    if (responseInProgress) return;
>>>>>>> 32052ba (pushed the missing files)
    if (isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

async function startVoiceRecording() {
    try {
<<<<<<< HEAD
=======
        if (responseInProgress) return;
>>>>>>> 32052ba (pushed the missing files)
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        
        // Use MediaRecorder which browsers support natively
        const mimeType = "audio/webm";
        mediaRecorder = new MediaRecorder(stream, { mimeType });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            try {
                // Collect all chunks into a single blob
                const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
                console.log(`[Voice] Recording complete: ${(audioBlob.size / 1024).toFixed(2)} KB`);
                
                // Convert WebM to WAV for backend
                console.log("[Voice] Converting WebM to WAV...");
                const wavBlob = await convertWebmToWav(audioBlob);
                console.log(`[Voice] Converted to WAV: ${(wavBlob.size / 1024).toFixed(2)} KB`);
                
                await transcribeAndSend(wavBlob, "wav");
            } catch (err) {
                console.error("[Voice] Error processing recordings:", err);
                hideTyping();
                appendMessage("❌ Recording error: " + err.message, "bot");
            }
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        document.getElementById("voice-btn").classList.add("recording");
        document.getElementById("voice-btn").textContent = "⏹️ Stop";
        console.log("[Voice] Recording started");
    } catch (err) {
        console.error("Microphone access denied:", err);
        alert("Please allow microphone access to use voice features.");
    }
}

// Convert WebM to WAV using Web Audio API
async function convertWebmToWav(webmBlob) {
    // Create audio context if not exists
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    try {
        // Decode WebM to PCM
        const arrayBuffer = await webmBlob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        const sampleRate = audioBuffer.sampleRate;
        const channels = audioBuffer.numberOfChannels;
        const length = audioBuffer.length;
        
        console.log(`[Voice] WebM decoded: ${channels} channels, ${length} samples, ${sampleRate}Hz`);
        
        // Get channel data
        let interleaved;
        if (channels === 2) {
            // Stereo to mono
            const left = audioBuffer.getChannelData(0);
            const right = audioBuffer.getChannelData(1);
            interleaved = new Float32Array(length);
            for (let i = 0; i < length; i++) {
                interleaved[i] = (left[i] + right[i]) / 2;
            }
        } else {
            // Already mono
            interleaved = audioBuffer.getChannelData(0);
        }
        
        // Encode to WAV
        return pcmToWav(interleaved, sampleRate);
    } catch (err) {
        console.error("[Voice] WebM decode error:", err);
        throw err;
    }
}

// Convert PCM audio data to WAV format
function pcmToWav(pcmData, sampleRate) {
    const numChannels = 1;
    const bitsPerSample = 16;
    
    // Create interleaved PCM data (mono)
    const interleaved = new Float32Array(pcmData);
    
    // Convert float32 to int16
    const int16Data = new Int16Array(interleaved.length);
    for (let i = 0; i < interleaved.length; i++) {
        let s = Math.max(-1, Math.min(1, interleaved[i]));
        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    
    const dataLength = int16Data.length * 2;
    const buffer = new ArrayBuffer(44 + dataLength);
    const view = new DataView(buffer);
    
    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };
    
    writeString(0, "RIFF");
    view.setUint32(4, 36 + dataLength, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * (bitsPerSample / 8), true);
    view.setUint16(32, numChannels * (bitsPerSample / 8), true);
    view.setUint16(34, bitsPerSample, true);
    writeString(36, "data");
    view.setUint32(40, dataLength, true);
    
    // Copy audio data
    let offset = 44;
    for (let i = 0; i < int16Data.length; i++) {
        view.setInt16(offset, int16Data[i], true);
        offset += 2;
    }
    
    return new Blob([buffer], { type: "audio/wav" });
}

function stopVoiceRecording() {
    if (mediaRecorder) {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById("voice-btn").classList.remove("recording");
        document.getElementById("voice-btn").textContent = "🎤 Voice";
    }
}

async function transcribeAndSend(audioBlob, audioFormat = "wav") {
    try {
<<<<<<< HEAD
=======
        if (responseInProgress) return;
>>>>>>> 32052ba (pushed the missing files)
        showTyping();
        
        console.log(`[Voice] Recording complete. Format: ${audioFormat}, Size: ${(audioBlob.size / 1024).toFixed(2)}KB`);
        console.log(`[Voice] Sending to: /transcribe`);
        
        // Create FormData for file upload
        const formData = new FormData();
        const filename = `audio.${audioFormat}`;
        formData.append("file", audioBlob, filename);

        // Send to gateway /transcribe endpoint (no CORS issues - same origin)
        const response = await fetch(`/transcribe`, {
            method: "POST",
            body: formData
        });

        console.log(`[Voice] Transcribe response: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            const errText = await response.text();
            console.error(`[Voice] Transcription error response:`, errText);
            hideTyping();
            appendMessage("❌ Transcription failed: " + errText, "bot");
            return;
        }

        const result = await response.json();
        console.log(`[Voice] Transcription success:`, result);
        const transcribedText = result.text;

        // Display transcribed text
        appendMessage(transcribedText, "user");

        // Send to conversation model via WebSocket
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.log("[Voice] WebSocket not ready, reconnecting...");
            ws = connectWebSocket();
            // Wait for connection
            setTimeout(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    sendToConversation(transcribedText);
                }
            }, 500);
        } else {
            sendToConversation(transcribedText);
        }
    } catch (err) {
        console.error("[Voice] Transcription error:", err);
        hideTyping();
        appendMessage("❌ Error: " + err.message, "bot");
    }
}

function sendToConversation(message) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error("WebSocket not connected");
        return;
    }

    console.log("[Voice] Sending message to conversation:", message);
    ws.send(JSON.stringify({
        session_id: sessionId,
        message: message
    }));
}

async function playResponse(text) {
    try {
        // Request TTS synthesis from gateway /synthesize endpoint (no CORS issues)
        const response = await fetch(`/synthesize`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                language: "en"
            })
        });

        if (!response.ok) {
            console.error("Synthesis failed:", response.status);
            return;
        }

        // Get audio blob (MP3 format from pyttsx3)
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        // Play audio
        const audioElement = document.getElementById("response-audio");
        audioElement.src = audioUrl;
        audioElement.play();
    } catch (err) {
        console.error("Audio playback error:", err);
    }
}

function stopTTS() {
    const audioElement = document.getElementById("response-audio");
    const stopButton = document.getElementById("stop-tts-btn");
    audioElement.pause();
    audioElement.currentTime = 0;
    stopButton.style.display = "none";
    console.log("[TTS] Stopped");
}

// Listen to audio playback events to show/hide stop button
document.addEventListener("DOMContentLoaded", function () {
    const audioElement = document.getElementById("response-audio");
    const stopButton = document.getElementById("stop-tts-btn");

    audioElement.addEventListener("play", function () {
        stopButton.style.display = "inline-block";
        console.log("[TTS] Playing - stop button visible");
    });

    audioElement.addEventListener("pause", function () {
        stopButton.style.display = "none";
        console.log("[TTS] Paused - stop button hidden");
    });

    audioElement.addEventListener("ended", function () {
        stopButton.style.display = "none";
        console.log("[TTS] Ended - stop button hidden");
    });

    audioElement.addEventListener("error", function () {
        stopButton.style.display = "none";
        console.log("[TTS] Audio error - stop button hidden");
    });
});

/* ────────────────────────────────────────────────────────────────── */
document.getElementById("message-input")
    .addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });

// On page load, test service connectivity
window.addEventListener("load", async () => {
    console.log("[Init] Testing service connectivity...");
    try {
        const gatewayHealth = await fetch(`/health`);
        if (gatewayHealth.ok) {
            const health = await gatewayHealth.json();
            console.log("[Init] Gateway health:", health);
        } else {
            console.error("[Init] Gateway returned:", gatewayHealth.status);
        }
    } catch (err) {
        console.error("[Init] Cannot reach gateway", err);
    }
});
