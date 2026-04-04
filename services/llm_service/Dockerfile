# ---------- LLM Service ----------
# Thin wrapper around Ollama that exposes a clean streaming HTTP API.
# Runs as its own container so the inference layer is independently scalable.

FROM python:3.11-slim

WORKDIR /app

# Install system TTS dependencies for pyttsx3 (espeak-ng) and audio libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    libespeak-ng1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
