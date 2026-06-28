# Local LLM Jarvis - Readiness TO-DO

This checklist covers what remains before this project should be considered a reliably usable app for daily personal use.

## 1. Must-Have Before Usable Release

## 1.1 Security and Privacy

- [ ] Force API key in non-development environments.
- [ ] Remove insecure default (`change-me-before-real-use`) from deploy path; require explicit secret setup.
- [ ] Restrict CORS and origin settings by environment.
- [ ] Add transport security plan for non-local access:
  - Tailscale-only policy or reverse-proxy TLS termination.
- [ ] Add sensitive-data logging policy and verify no personal content is accidentally logged.
- [ ] Add backup encryption at rest policy for database and document content.

## 1.2 Data Safety and Schema Evolution

- [ ] Add Alembic migrations and baseline migration from current models.
- [ ] Add startup check to fail fast if migrations are pending.
- [ ] Add retention controls for conversation and logs (manual delete and optional auto-prune).
- [ ] Add document and memory delete/export workflows in user-facing clients.
- [ ] Add backup/restore runbook with tested restore drill.

## 1.3 Reliability and Operations

- [ ] Add structured logging with request IDs and error categorization.
- [ ] Add metrics endpoint (latency, error counts, dependency health).
- [ ] Add health/readiness split:
  - liveness for process
  - readiness for DB and optional Ollama availability
- [ ] Add restart/backoff strategy notes for each service in production-like setup.
- [ ] Add container healthchecks and startup ordering constraints.
- [ ] Add monitoring/alerting minimums for API uptime and error rate.

## 1.4 Android Usability Baseline

- [ ] Add reminder actions in notifications (Done, Snooze, Open app).
- [ ] Add explicit reminder timezone/date formatting for better readability.
- [ ] Add robust offline/network error states and retry actions.
- [ ] Add loading/sync indicators for each section, not only global state.
- [ ] Add in-app create/edit flows for reminders and tasks (not only quick capture).
- [ ] Add accessibility pass (touch target sizes, content descriptions, contrast checks).

## 1.5 Web Usability Baseline

- [ ] Add task complete/edit controls in UI.
- [ ] Add reminder create/edit/complete controls in UI.
- [ ] Add document delete action and confirmation.
- [ ] Show document ask context snippets in UI for explainability.
- [ ] Improve API error display with actionable messages.
- [ ] Add responsive UX polish for narrow mobile screens.

## 1.6 Functional Correctness

- [ ] Expand natural language time parsing:
  - explicit dates
  - weekdays
  - timezone-safe handling
  - recurring expressions (every day/every Monday)
- [ ] Reduce false positives in task/reminder/log extraction heuristics.
- [ ] Add idempotency strategy for duplicate captures (same text sent repeatedly).
- [ ] Add conflict handling for ambiguous captures (clarifying question flow).

## 1.7 Test Coverage and CI

- [ ] Add backend tests for all routers (tasks, reminders, logs, memory CRUD variants).
- [ ] Add failure-mode tests (invalid API key, oversized docs, unsupported file types, Ollama down).
- [ ] Add integration tests for document upload/delete lifecycle.
- [ ] Add Android tests for API parsing and reminder worker behavior.
- [ ] Add web tests for quick capture and document flows.
- [ ] Add CI pipeline for lint/test/build on each push/PR.

## 2. Should-Have for Strong MVP

## 2.0 Standout Product Epics

- [x] Projects engine:
  - project create flow with objective, constraints, deadline, and success criteria
  - project planning API that generates milestones, timeline, and sequenced tasks
  - project progress state model (planned/active/blocked/done)
  - project replan flow when slippage risk is detected
- [ ] Goals engine:
  - goal create flow with timeframe and desired outcome
  - baseline interview/questionnaire workflow
  - automated daily/weekly reminder program generation
  - checkpoint and recalibration logic based on adherence/performance
- [ ] Habits engine:
  - habit create flow for build/remove modes
  - trigger/context capture and replacement-action design
  - recurring reminders and accountability check-ins
  - streak, relapse, and recovery tracking model
- [ ] Automations engine:
  - memory/event trigger rules to generate project/goal/habit suggestions
  - suggestion explainability ("why this was suggested")
  - accept/snooze/dismiss controls
  - automation settings per category
- [ ] Tracking dashboards:
  - daily scorecard (goals/habits/tasks)
  - weekly trend analysis
  - project progress dashboard
  - retrospective summary generator with concrete next-step suggestions

## 2.1 Product Features

- [ ] Memory management screens in Android and web (list/edit/deactivate).
- [ ] Conversation history view and controls.
- [ ] Better Today suggestions using more than top-item fallback logic.
- [ ] Manual task prioritization controls with explainability.

## 2.2 Document Intelligence

- [ ] Support PDF and DOCX ingestion.
- [ ] Add chunk citation metadata (chunk number/offset) to answers.
- [ ] Add optional embeddings-based retrieval for better semantic matching.
- [ ] Add document-level permissions or labels for privacy categories.

## 2.3 Notifications and Reminder Engine

- [ ] Add snooze/reschedule API and client controls.
- [ ] Add recurring reminder model and scheduler support.
- [ ] Move from polling-only reminders to more precise local scheduling when possible.

## 2.4 Performance

- [ ] Add pagination for large list endpoints.
- [ ] Add indexes and query-plan checks for expected high-volume tables.
- [ ] Add API response compression where appropriate.
- [ ] Add rate limiting strategy for expensive endpoints (document ask).

## 3. Nice-to-Have After Usable Baseline

- [ ] Health Connect integration.
- [ ] Calendar integration.
- [ ] Voice-native in-app capture.
- [ ] Multi-user support and per-user data segregation.
- [ ] Rich analytics dashboard for routines and completion trends.
- [ ] Predictive guidance for "at-risk" goals/projects.
- [ ] Adaptive coaching style that changes by engagement pattern.

## 4. Documentation and Consistency Fixes

- [ ] Update Android README to remove or correct references to unimplemented voice capture.
- [ ] Reconcile web README "future work" list with currently implemented document features.
- [ ] Add explicit "supported file types and limits" section in top-level README.
- [ ] Add operator runbook:
  - deployment
  - rollback
  - backup/restore
  - incident response

## 5. Release Exit Criteria (Suggested)

Treat the app as "usable" when all conditions below are met:

- [ ] Core workflows pass manual acceptance:
  - quick capture creates correct task/reminder/log entries
  - Today view reflects updates quickly
  - Android reminder notification appears and is actionable
  - Web document upload and Q&A works with understandable responses
- [ ] Critical security controls are in place (API key enforced, secrets handled safely).
- [ ] Backup and restore tested successfully at least once.
- [ ] Automated tests cover critical API and client flows.
- [ ] Error handling is user-friendly on Android and web for offline and dependency failures.
