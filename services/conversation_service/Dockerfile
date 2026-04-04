# ---------- Conversation Service ----------
# Handles session state, conversation history, and prompt orchestration.
# Calls the LLM Service for inference — no direct Ollama dependency.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
