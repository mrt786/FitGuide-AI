/**
 * FitGuide AI — Frontend WebSocket Client
 *
 * Key change for microservices: The WebSocket URL is now derived from
 * the current page URL (window.location) instead of being hardcoded.
 * This means the frontend works regardless of whether the server runs
 * on localhost:8000, a Docker container, or a deployed domain.
 */

let sessionId = generateSessionId();
let ws = null;
let currentBotMessage = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

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
            currentBotMessage = null;
            return;
        }

        // Handle error messages from the gateway
        if (event.data.startsWith("[ERROR]")) {
            hideTyping();
            if (!currentBotMessage) {
                currentBotMessage = appendMessage("", "bot");
            }
            currentBotMessage.textContent = "⚠️ " + event.data.replace("[ERROR] ", "");
            currentBotMessage.style.color = "#dc2626";
            currentBotMessage = null;
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
    if (!message) return;

    // Reconnect if needed
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        ws = connectWebSocket();
        // Wait for connection then retry
        setTimeout(() => sendMessage(), 500);
        return;
    }

    appendMessage(message, "user");
    showTyping();

    ws.send(JSON.stringify({
        session_id: sessionId,
        message: message
    }));

    input.value = "";
}

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
    // Reconnect WebSocket for clean state
    if (ws) ws.close();
    ws = connectWebSocket();
}

/* ENTER KEY SUPPORT */
document.getElementById("message-input")
    .addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
