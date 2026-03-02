# Conversational AI - Local Setup Guide

## 1. Setup Ollama Locally

Run the following command in **PowerShell** to install Ollama:

```powershell
irm https://ollama.com/install.ps1 | iex
```

## 2. Load the Model

Run the following command to download and load the **phi3** model:

```bash
ollama run phi3
```

This will load the `phi3:latest` model.

## 3. Verify the API is Working

Test the Ollama API by sending a request:

```powershell
Invoke-RestMethod -Uri "http://localhost:11434/api/generate" `
  -Method Post `
  -Body '{"model":"phi3:latest","prompt":"Hello","stream":false}' `
  -ContentType "application/json"
```

If everything is working correctly, you should see a response like this:

```
model                : phi3:latest
created_at           : 2026-03-02T13:56:05.8303643Z
response             : Greetings! How can I help you today?
done                 : True
done_reason          : stop
context              : {32010, 29871, 13, 10994...}
total_duration       : 2569844200
load_duration        : 127137500
prompt_eval_count    : 10
prompt_eval_duration : 865902000
eval_count           : 12
eval_duration        : 1538002100
```
