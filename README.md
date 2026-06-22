# Local LLM Jarvis

An MVP implementation of a fully local, Ollama-powered personal assistant served over a private Docker/Tailscale network.

The current slice focuses on the core loop:

- Capture natural-language input.
- Extract tasks, reminders, water logs, and nutrition logs.
- Prioritize tasks.
- Expose a Today view for Android and web clients.
- Upload and ask questions about text-based documents.
- Protect private endpoints with an API key.
- Notify Android users about due reminders.
- Keep Ollama optional for conversational fallback while deterministic tools mature.

## Product Direction: Beyond Calendar

The current MVP proves the local-assistant foundation, but the intended product is broader than reminders and tasks.
The next phase centers on five standout capabilities:

1. Projects:
   - User provides an objective and constraints.
   - Assistant generates a phased plan, timeline, milestones, and actionable tasks.
   - Assistant monitors progress and dynamically replans when slip risk appears.
2. Goals:
   - User defines long-term outcomes (for example fitness, learning, performance goals).
   - Assistant asks baseline questions and builds a realistic program by timeframe.
   - Assistant schedules reminders, check-ins, and progress reviews.
3. Habits:
   - User specifies habits to build or reduce.
   - Assistant designs cue-routine-reward style loops, reminders, and accountability prompts.
   - Assistant tracks streaks, misses, and trigger patterns.
4. Automations:
   - Memory-driven suggestions for new projects, habits, and goals.
   - Trigger-based nudges (for example repeated misses -> lighter plan suggestion).
   - Weekly auto-generated planning and reflection prompts.
5. Tracking Dashboards:
   - Daily/weekly dashboard for goals, habits, projects, and task completion.
   - Trend visualizations and retrospective summaries.
   - Assistant-generated next-step recommendations.

Related differentiators planned with these:

- Adaptive daily planning (energy/time-aware scheduling).
- Accountability mode (gentle, standard, strict coaching styles).
- Personal playbooks (repeatable routines for common project types).
- Retrospective sessions with actionable course-correction suggestions.

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
- Task completion.
- Reminder notifications.
- API URL settings.
- API key settings.

## Current Publishable MVP Status

The app is now text-first. For voice dictation, use the Android keyboard's built-in microphone input, such as Google Keyboard voice typing.

Implemented publishable foundations:

- Dockerized backend, web, Postgres, and Ollama.
- API-key authentication with `X-API-Key`.
- Android text capture and Today workflow.
- Android due-reminder notifications through WorkManager.
- Web document upload and document Q&A.
- Backend tests for auth, assistant capture, Today, and documents.

## MVP Services

- `api`: FastAPI backend.
- `web`: minimal companion web app.
- `postgres`: primary data store.
- `ollama`: local LLM runtime.

## Useful API Calls

Create an assistant action:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/assistant/message `
  -Headers @{"X-API-Key"="change-me-before-real-use"} `
  -ContentType "application/json" `
  -Body '{"text":"Add a task to submit the insurance form tomorrow morning","source":"web"}'
```

Get the Today view:

```powershell
Invoke-RestMethod http://localhost:8000/today -Headers @{"X-API-Key"="change-me-before-real-use"}
```

## Design

See [SOLUTION_DESIGN.md](./SOLUTION_DESIGN.md) for the full product and technical design.

## Roadmap Docs

- Current capability inventory: [FEATURES_CURRENT.md](./FEATURES_CURRENT.md)
- Usability and launch checklist: [TODO_BEFORE_USABLE.md](./TODO_BEFORE_USABLE.md)
- Service-level assessment: [SLA_REVIEW.md](./SLA_REVIEW.md)
