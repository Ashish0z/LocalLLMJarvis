# Local LLM Jarvis - Current Feature Inventory

This document lists features that are currently implemented in this repository.
It focuses on what is actually available today across backend, Android, web, and deployment.

## 1. Platform and Deployment

- Docker Compose stack with four services:
  - FastAPI backend (`api`)
  - Vite web companion (`web`)
  - PostgreSQL (`postgres`)
  - Ollama runtime (`ollama`)
- Host-exposed ports:
  - API: `8000`
  - Web: `5173`
  - Postgres: `5432`
  - Ollama: `11434`
- Environment-driven runtime configuration for database, API key, CORS origins, Ollama URL/model, and max document size.
- Health endpoint: `GET /health`.

## 2. Security and Access Control

- Optional API key enforcement via `X-API-Key` header:
  - If `JARVIS_API_KEY` is set, protected routes require matching key.
  - If `JARVIS_API_KEY` is empty, protected routes are open (development-friendly mode).
- Protected route groups:
  - `/today`
  - `/assistant`
  - `/tasks`
  - `/reminders`
  - `/logs`
  - `/memory`
  - `/documents`
  - `/projects`
- CORS middleware enabled with configurable allowed origins.

## 3. Data Model and Persistence

Current persisted entities (SQLAlchemy models):

- `tasks`
  - Title, notes, status, due date/time, priority score/reason, source, timestamps.
- `reminders`
  - Title, remind date/time, status, intensity, source, timestamps.
- `health_logs`
  - Kind, value, amount/unit, timestamp, source.
- `memory_items`
  - Category, content, source, active flag, timestamps.
- `conversation_messages`
  - Role (`user`/`assistant`), content, timestamp.
- `documents`
  - Filename, content type, full text, summary, source, timestamps.
- `document_chunks`
  - Document reference, chunk index, chunk text, timestamp.
- `projects`
  - Title, objective, constraints, deadline, status (planned/active/blocked/done), replan notes, timestamps.
- `milestones`
  - Project reference, title, description, sequence order, status (planned/active/blocked/done), due date, timestamps.

Database initialization is automatic on API startup (`create_all`).

## 4. Backend API Capabilities

### 4.1 Assistant Capture

- Endpoint: `POST /assistant/message`
- Input: free-form text + source (`chat`, `web`, `android`).
- Behavior:
  - Attempts deterministic extraction for:
    - Task creation (keyword-driven)
    - Reminder creation (`remind me` / `reminder`)
    - Water logs (with ml/l amount parsing)
    - Nutrition logs (meal-related markers)
  - Parses rough due/reminder times from phrases (for example: tomorrow, morning, 3 pm, after lunch).
  - If no deterministic action is detected, attempts Ollama fallback chat response.
  - Stores user and assistant messages in conversation history.
  - Returns structured `actions` list and response text.

### 4.2 Today View

- Endpoint: `GET /today`
- Returns:
  - Top 3 pending tasks by highest priority score
  - Up to 5 upcoming active reminders
  - Up to 5 most recent health logs
  - Generated suggestion string based on current data

### 4.3 Tasks

- `POST /tasks` create task with computed priority score/reason.
- `GET /tasks` list tasks (default filter: `pending`, configurable limit).
- `PATCH /tasks/{task_id}` update task fields and recompute priority when title/due date changes.

### 4.4 Reminders

- `POST /reminders` create reminder with intensity (`gentle`, `standard`, `persistent`).
- `GET /reminders` list reminders (default filter: `active`, configurable limit).
- `PATCH /reminders/{reminder_id}` update reminder fields.

### 4.5 Health Logs

- `POST /logs` generic health log (`water`, `nutrition`, `sleep`, `mood`, `exercise`).
- `POST /logs/water` convenience water endpoint.
- `POST /logs/nutrition` convenience nutrition endpoint.
- `GET /logs` list logs with optional `kind` filter.

### 4.6 Memory

- `POST /memory` create memory item.
- `GET /memory` list memory items (default `active_only=true`).
- `PATCH /memory/{memory_id}` update category/content/active state.

### 4.7 Documents and Q&A

- `POST /documents` upload document and index chunks.
  - Supported types: text, markdown, csv, json, log.
  - Max size limit enforced (`max_document_bytes`).
  - Auto-summary stored.
- `GET /documents` list uploaded documents.
- `GET /documents/{document_id}` retrieve document details (including text).
- `DELETE /documents/{document_id}` remove document and its chunks.
- `POST /documents/{document_id}/ask` ask questions against selected document.
  - Uses chunk ranking by term overlap.
  - Builds context-constrained prompt.
  - Uses Ollama for answer when available.
  - Returns selected context chunks even when Ollama is unavailable.

## 5. Assistant Intelligence (Current Scope)

- Rule-based intent extraction for common personal assistant actions.
- Simple natural language time parsing (relative dates + coarse dayparts + clock values).
- Heuristic task prioritization:
  - urgency words
  - low-urgency words
  - due-date proximity/overdue status
- Ollama used as fallback conversational responder, not as a mandatory dependency for deterministic capture actions.

## 6. Android App Capabilities

- Jetpack Compose single-screen MVP with:
  - Today summary card
  - Quick capture text input
  - Assistant response display
  - Top priority tasks list
  - Task completion action (mark done)
  - Upcoming reminders list
  - Settings for API base URL and API key
- Stores API URL and API key in SharedPreferences.
- Uses backend API endpoints:
  - `GET /today`
  - `POST /assistant/message`
  - `PATCH /tasks/{id}`
  - `GET /reminders`
- Periodic reminder polling using WorkManager (15-minute interval):
  - Fetches reminders
  - Triggers local notifications when due
  - Deduplicates notifications per reminder ID
- Requests Android notification permission (Android 13+).
- Manifest includes cleartext traffic support for local HTTP URLs.

## 7. Web Companion Capabilities

- React + Vite web companion with:
  - Configurable API URL and API key
  - Quick capture form tied to `POST /assistant/message`
  - Today view panel showing suggestion, top priorities, reminders
  - Document upload UI
  - Document list and selection
  - Document Q&A interface tied to `POST /documents/{id}/ask`
- Persists API URL and API key in localStorage.

## 8. Testing and Quality Signals

- Automated backend tests (`pytest`) currently cover:
  - public health endpoint
  - API key protection on `/today`
  - assistant task creation + Today integration
  - document upload + ask flow and context chunk selection

## 9. Known Functional Boundaries (Current Feature Set)

- No first-class user account system; API key is global.
- No database migration framework (schema created from models at startup).
- Document processing is text-only; no PDF/DOCX/image extraction pipeline.
- Reminder notifications on Android are periodic-poll based, not exact alarm scheduling.
- Voice capture, calendar integration, Health Connect ingestion, and advanced memory reasoning are not implemented in code yet.

## 10. Planned Standout Capabilities (Not Yet Implemented)

The product direction includes the following differentiators, which are documented in design and roadmap files but are not yet implemented in this repository:

- Projects:
  - project objective capture
  - assistant-generated milestones, timeline, and task plan
  - dynamic replanning from progress changes
- **Projects Engine** (implemented — see `/projects` API):
  - `POST /projects` — create a project with objective, constraints, deadline, and sequenced milestones
  - `GET /projects` — list projects, filterable by status
  - `GET /projects/{id}` — retrieve project with full milestone plan
  - `PATCH /projects/{id}` — update project fields or transition state (planned → active → blocked → done)
  - `POST /projects/{id}/milestones` — add a milestone to a project
  - `PATCH /projects/{id}/milestones/{ms_id}` — update or advance a milestone
  - `POST /projects/{id}/replan` — record slippage reason and replace milestone plan; auto-unblocks project
- Goals:
  - long-term goal setup with baseline interview
  - timeframe-based daily/weekly programs
  - adaptive reminders and periodic reassessment
- Habits:
  - build/remove habit flows
  - cue/trigger-aware reminder strategy
  - streak and relapse accountability support
- Automations:
  - memory-driven suggestions for projects/goals/habits
  - trigger-based proactive nudges and weekly planning prompts
  - explainable suggestions with accept/snooze/dismiss controls
- Tracking dashboards:
  - daily scorecards
  - weekly trend views
  - retrospective summaries and course-correction guidance
