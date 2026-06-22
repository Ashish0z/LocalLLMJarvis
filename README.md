# Local LLM Jarvis

An MVP implementation of a fully local, Ollama-powered personal assistant served over a private Docker/Tailscale network.

The current slice focuses on the core loop:

- Capture natural-language input.
- Extract tasks, reminders, water logs, and nutrition logs.
- Prioritize tasks.
- Expose a Today view for Android and web clients.
- Keep Ollama optional for conversational fallback while deterministic tools mature.

## Apps

- `android`: Kotlin + Jetpack Compose Android MVP client.
- `web`: lightweight web companion for quick capture and Today view.
- `backend`: FastAPI assistant API.

## Complete Setup Guide

Use [SETUP.md](./SETUP.md) for the full installation and deployment path:

- Base requirements.
- Docker deployment.
- Postgres setup.
- Ollama model setup.
- Tailscale private network setup.
- Android APK creation.

## Quick Start

1. Copy environment defaults:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start the local stack:

   ```powershell
   docker compose up --build
   ```

3. Open:

   - API: `http://localhost:8000/docs`
   - Web companion: `http://localhost:5173`
   - Ollama: `http://localhost:11434`

4. Pull a local model if Ollama does not already have one:

   ```powershell
   docker compose exec ollama ollama pull llama3.1:8b
   ```

## Android App

Open the [android](./android) folder in Android Studio and run the `app` configuration.

The Android app defaults to `http://10.0.2.2:8000`, which works from the Android Emulator when the backend is running on the host machine.

For a physical phone over Tailscale, open Settings in the app and set the API URL to your private backend address, for example:

```text
http://your-tailscale-hostname:8000
```

Current Android MVP features:

- Today screen.
- Text capture.
- Voice capture using Android speech recognition.
- Task completion.
- API URL settings.

## MVP Services

- `api`: FastAPI backend.
- `web`: minimal companion web app.
- `postgres`: primary data store.
- `ollama`: local LLM runtime.

## Useful API Calls

Create an assistant action:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/assistant/message `
  -ContentType "application/json" `
  -Body '{"text":"Add a task to submit the insurance form tomorrow morning"}'
```

Get the Today view:

```powershell
Invoke-RestMethod http://localhost:8000/today
```

## Design

See [SOLUTION_DESIGN.md](./SOLUTION_DESIGN.md) for the full product and technical design.
