# Local LLM Jarvis - SLA Review

## 1. Purpose

This review evaluates current SLA readiness for the Local LLM Jarvis project and defines practical service-level targets for a self-hosted, private-network assistant.

Scope reviewed:

- Backend API
- Android app critical flows
- Web companion critical flows
- Dependencies: PostgreSQL and Ollama

## 2. Current SLA Posture (As Implemented)

### 2.1 Positive Baseline

- Health endpoint exists (`GET /health`).
- API key protection exists for private routes.
- Core CRUD-like flows for tasks/reminders/logs/memory/documents are implemented.
- Dockerized deployment exists for reproducible startup.
- Basic automated tests validate key pathways.

### 2.2 SLA Gaps

- No formal SLO/SLA definitions currently documented.
- No readiness probe that verifies dependency health (DB/Ollama).
- No observability stack (metrics, dashboards, alerts).
- No explicit backup/restore SLO and no restoration test evidence in repo.
- No incident-management runbook or escalation policy.
- No client-facing graceful degradation policy when Ollama is unavailable.
- No defined latency/error budgets and no trend tracking.
- Android reminder execution depends on 15-minute periodic polling, which weakens reminder-time accuracy guarantees.

Result: current posture is suitable for development and personal experimentation, but not yet strong enough for a dependable daily-use SLA commitment.

## 3. Recommended Initial SLA Targets (Phase 1)

These are realistic targets for a single-user private deployment.

### 3.1 Availability

- API availability target: 99.0% monthly.
- Today and capture endpoints availability target: 99.0% monthly.
- Document upload/ask availability target: 97.0% monthly (dependency on Ollama and larger processing paths).

### 3.2 Performance

- `GET /today` p95 response time: <= 800 ms.
- `POST /assistant/message` p95 response time:
  - deterministic action path: <= 1.2 s
  - Ollama fallback path: <= 12 s
- `POST /documents` (small text files <= 1 MB) p95 completion: <= 3 s.
- `POST /documents/{id}/ask` p95:
  - with Ollama available: <= 15 s
  - without Ollama: <= 2 s with deterministic fallback message.

### 3.3 Reliability / Error Rate

- 5xx error rate target: < 1.0% of requests per rolling 24-hour window.
- Auth failures (401) excluded from server-error budget.

### 3.4 Data Protection

- Backup frequency target: daily full logical backup of Postgres.
- Retention target: 7 daily restore points minimum.
- Recovery Point Objective (RPO): <= 24 hours.
- Recovery Time Objective (RTO): <= 4 hours for single-node restore.

### 3.5 Reminder Delivery (Android)

- Due-reminder notification timeliness target: within 15 minutes of due time for polling-based mode.
- Missed-reminder tolerance: <= 2% monthly for reminders with valid due timestamps and available network.

### 3.6 Standout Feature Targets (Projects, Goals, Habits, Automations, Dashboards)

- Project plan generation p95 time: <= 20 s for medium-size plans.
- Goal baseline interview completion success: >= 90% of started interviews.
- Habit check-in prompt delivery success: >= 98% for scheduled prompts.
- Automation suggestion precision target: >= 70% user acceptance or snooze (not dismiss) in first 90 days.
- Dashboard freshness target: metrics update within <= 5 minutes of source-event write.

## 4. SLA Risk Assessment by Component

## 4.1 Backend API

Risk level: Medium

Primary risks:

- Startup schema creation without migrations can lead to drift and risky upgrades.
- No request tracing/metrics means outages may be detected late.
- Dependency failures are not surfaced through readiness states.

## 4.2 PostgreSQL

Risk level: Medium

Primary risks:

- No documented backup automation in repository.
- No tested restoration evidence.

## 4.3 Ollama Dependency

Risk level: Medium to High (for conversational/document-answer quality)

Primary risks:

- Model availability is external to API process and may be missing at startup.
- Slow model responses can dominate p95 latency.
- Feature behavior differs when Ollama is offline.

## 4.4 Android Reminders

Risk level: Medium

Primary risks:

- WorkManager periodic polling is not an exact alarm mechanism.
- Notification permission denial disables alerts.
- Network/API failures can delay reminder sync and delivery.

## 4.5 Web Companion

Risk level: Low to Medium

Primary risks:

- No robust retry/backoff UX for API failures.
- Error handling exists but is basic for production-like reliability.

## 5. Gap-to-Target Action Plan

## 5.1 Monitoring and Alerting

- Add API metrics collection (request count, status classes, latency histograms).
- Add alerts for:
  - API unavailable > 5 minutes
  - error-rate spike > threshold
  - dependency health degradation

## 5.2 Health and Readiness

- Keep `/health` as liveness endpoint.
- Add `/ready` endpoint validating:
  - database connectivity
  - optional Ollama reachability status

## 5.3 Backup and Recovery

- Implement scheduled Postgres backups.
- Document restore steps in a runbook.
- Run and record monthly recovery drill results.

## 5.4 Change Management

- Add Alembic migrations.
- Define release checklist including migration, smoke tests, and rollback path.

## 5.5 Client Reliability

- Android: add explicit reminder failure state visibility and actionable notification controls.
- Web: add retry controls and clearer failure messaging for document operations.

## 5.6 Standout Feature Reliability Controls

- Define deterministic fallback when LLM planning fails:
  - project templates
  - goal starter plans
  - habit starter protocols
- Add audit log for automated suggestions:
  - trigger source
  - decision rationale
  - user outcome (accepted/snoozed/dismissed)
- Add data quality checks for dashboard pipelines to avoid misleading retrospectives.
- Add safeguards to prevent notification overload from goals + habits + projects combined.

## 6. Proposed SLA Communication Template

Use this plain-language commitment for private beta users:

- "The assistant is targeted for 99% monthly API uptime."
- "Core capture and Today features are prioritized for availability over advanced LLM response quality."
- "Data is backed up daily with recovery target within 4 hours and up to 24 hours of potential data loss in worst-case restore scenarios."
- "Reminder timing is near-real-time but currently designed for up to 15-minute delay due to background polling constraints."

## 7. SLA Readiness Verdict

Current verdict: Not SLA-ready for dependable daily-use commitments yet.

Reason summary:

- Core functionality exists and is cohesive.
- Operational controls required for SLA confidence (observability, backup discipline, migrations, runbooks) are not yet in place.

Expected outcome after action plan completion:

- Suitable for an initial private single-user SLA with clear boundaries.
