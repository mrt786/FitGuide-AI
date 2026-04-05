let sessionId = generateSessionId();
let ws = connectWebSocket();
let currentBotMessage = null;
let responseInProgress = false;

function generateSessionId() {
    return Math.random().toString(36).substring(2);
}

function connectWebSocket() {
    const socket = new WebSocket("ws://127.0.0.1:8000/ws/chat");

    socket.onmessage = function(event) {
        if (event.data === "[END]") {
            hideTyping();
            setInputEnabled(true);
            responseInProgress = false;
            currentBotMessage = null;
            return;
        }

        if (event.data === "[ERROR]") {
            hideTyping();
            setInputEnabled(true);
            responseInProgress = false;
            currentBotMessage = null;
            appendMessage("Something went wrong while generating the response.", "bot");
            return;
        }

        if (!currentBotMessage) {
            currentBotMessage = appendMessage("", "bot");
        }

        currentBotMessage.textContent += event.data;
        scrollToBottom();
    };

    return socket;
}

function sendMessage() {
    if (responseInProgress) return;

    const input = document.getElementById("message-input");
    const message = input.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    showTyping();
    responseInProgress = true;
    setInputEnabled(false);

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

function setInputEnabled(enabled) {
    const input = document.getElementById("message-input");
    const sendButton = document.getElementById("send-button");
    const newButton = document.getElementById("new-button");

    input.disabled = !enabled;
    sendButton.disabled = !enabled;
    newButton.disabled = !enabled;

    if (enabled) {
        input.focus();
    }
}

function resetSession() {
    if (responseInProgress) return;

    sessionId = generateSessionId();
    document.getElementById("chat-box").innerHTML = "";
}

/* 🔥 ENTER KEY SUPPORT */
document.getElementById("message-input")
    .addEventListener("keydown", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
});