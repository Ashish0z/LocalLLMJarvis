# Backend Setup

This directory contains the FastAPI assistant API.

The backend is normally run through Docker Compose from the repository root. It connects to:

- Postgres for persistent data.
- Ollama for local LLM fallback responses.
- The web and Android clients through HTTP.

## Product Expansion Areas (Planned)

The backend roadmap expands from tasks/reminders into:

- Projects API:
  - create project objective
  - generate milestones, timelines, and scoped task plans
  - progress updates and replanning
- Goals API:
  - baseline questionnaire capture
  - long-horizon plans and adaptive reminders
  - checkpoint evaluation
- Habits API:
  - habit setup for build/remove modes
  - streak and relapse tracking
  - accountability workflows
- Automations API:
  - memory/event-triggered suggestion generation
  - explainability metadata and user feedback loop
- Dashboard API:
  - daily and weekly aggregate metrics
  - retrospective summaries and trend snapshots

## Files

- `Dockerfile`: backend container image.
- `requirements.txt`: Python dependencies.
- `app/main.py`: FastAPI application entry point.
- `app/models.py`: SQLAlchemy database models.
- `app/routers`: API endpoints.
- `app/services`: assistant, time parsing, prioritization, and Ollama client logic.

## Run with Docker

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build api postgres ollama
```

Open:

```text
http://localhost:8000/docs
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## Database

The backend uses this default Docker database URL:

```env
DATABASE_URL=postgresql+psycopg://jarvis:jarvis@postgres:5432/jarvis
```

Postgres is exposed to the host at:

```text
localhost:5432
```

Open a database shell:

```powershell
docker compose exec postgres psql -U jarvis -d jarvis
```

Useful checks:

```sql
\dt
select id, title, status, priority_score from tasks;
select id, title, status from reminders;
select id, kind, value, logged_at from health_logs;
```

## Ollama

The backend reads:

```env
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
```

Pull the model:

```powershell
docker compose exec ollama ollama pull llama3.1:8b
```

If the model is not available, deterministic actions still work for simple tasks, reminders, water logs, and meal logs. LLM fallback chat responses will be unavailable until the model is pulled.

## API Smoke Test

Create a task through the assistant:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/assistant/message `
  -ContentType "application/json" `
  -Body '{"text":"Add a task to submit the insurance form tomorrow morning","source":"web"}'
```

Get the Today view:

```powershell
Invoke-RestMethod http://localhost:8000/today
```

Log water:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/logs/water `
  -ContentType "application/json" `
  -Body '{"amount":300,"unit":"ml"}'
```

## Local Python Run

Docker is recommended. For local backend-only debugging:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "sqlite:///./local_jarvis.db"
uvicorn app.main:app --reload --app-dir backend
```

Open:

```text
http://localhost:8000/docs
```

The SQLite path is only for development convenience. Use Postgres for the real MVP deployment.

## Tailscale Access

When Docker Compose is running on the server machine, the Android app can reach the API over Tailscale with:

```text
http://100.x.y.z:8000
```

or with MagicDNS:

```text
http://your-machine-name:8000
```

Keep the host firewall enabled and avoid exposing the API publicly.

