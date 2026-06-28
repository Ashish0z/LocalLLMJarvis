# Local LLM Jarvis – Operations Runbook

This runbook covers alert thresholds, on-call procedures, and recovery steps for the
Local LLM Jarvis self-hosted deployment.

---

## 1. Endpoints Reference

| Endpoint        | Auth required | Purpose                                      |
|-----------------|---------------|----------------------------------------------|
| `GET /health`   | No            | Liveness probe – process is alive            |
| `GET /ready`    | No            | Readiness probe – DB and Ollama reachable    |
| `GET /metrics`  | No            | In-process request counts, error rate, p95   |

---

## 2. Alert Thresholds

### 2.1 API Availability

| Signal                           | Warning threshold | Critical threshold | Action                    |
|----------------------------------|-------------------|--------------------|---------------------------|
| `/health` HTTP 200 success rate  | < 99.5% / 5 min   | < 98% / 5 min      | See §4.1 API Down         |
| `/ready` `database.status`       | `error` once      | `error` > 1 min    | See §4.2 DB Unavailable   |
| `/ready` `ollama.status`         | `unavailable` once| `unavailable` > 5 min | See §4.3 Ollama Down   |

### 2.2 Error Rate

| Signal                    | Warning  | Critical | Action                       |
|---------------------------|----------|----------|------------------------------|
| `error_rate_5xx` (metrics)| > 1%     | > 5%     | See §4.4 High Error Rate     |
| `error_4xx` spike         | +50% vs  | +200% vs | Investigate auth/input issues|
|                           | baseline | baseline |                              |

### 2.3 Latency

| Signal                  | Warning   | Critical   | Action                        |
|-------------------------|-----------|------------|-------------------------------|
| `latency_ms.p95` (metrics) | > 800 ms | > 2 000 ms | See §4.5 High Latency       |
| `latency_ms.p99`        | > 2 000 ms| > 5 000 ms | Escalate, check Ollama        |

---

## 3. Health Check Verification

Quickly verify service health from the command line:

```bash
# Liveness
curl -sf http://localhost:8000/health | python3 -m json.tool

# Readiness (exit code 0 = ok, non-zero = degraded)
curl -sf http://localhost:8000/ready | python3 -m json.tool

# Current metrics snapshot
curl -sf http://localhost:8000/metrics | python3 -m json.tool
```

Expected healthy `/ready` response:
```json
{
  "status": "ok",
  "checks": {
    "database": { "status": "ok" },
    "ollama":   { "status": "ok" }
  }
}
```

---

## 4. Recovery Runbooks

### 4.1 API Process Down

**Symptoms:** `/health` unreachable, Docker container exited.

**Steps:**
1. `docker compose ps api` – confirm state.
2. `docker compose logs --tail=50 api` – review startup errors.
3. `docker compose restart api` – attempt recovery.
4. If restart fails, check environment variables (`.env`) and DB connectivity.
5. If persistent, redeploy: `docker compose up -d --force-recreate api`.

---

### 4.2 Database Unavailable

**Symptoms:** `/ready` returns `database.status = "error"`, 500s on data routes.

**Steps:**
1. `docker compose ps postgres` – check container status.
2. `docker compose logs --tail=50 postgres` – look for lock/crash/disk errors.
3. `docker compose restart postgres` – transient restart.
4. Verify connectivity: `docker compose exec postgres pg_isready -U jarvis`.
5. If data corruption is suspected, restore from latest backup (see §5).

---

### 4.3 Ollama Unavailable

**Symptoms:** `/ready` returns `ollama.status = "unavailable"`. LLM-backed features
(assistant message classification, document Q&A) may degrade to deterministic fallbacks.

**Steps:**
1. `docker compose ps ollama` – check container state.
2. `docker compose logs --tail=50 ollama` – look for model-load or GPU errors.
3. `docker compose restart ollama` – attempt recovery.
4. Verify model is loaded: `curl http://localhost:11434/api/tags`.
5. Pull the configured model if missing:
   `docker compose exec ollama ollama pull llama3.1:8b`.

> Note: Core capture and Today flows continue to work when Ollama is offline. Only
> LLM-enhanced paths are affected.

---

### 4.4 High 5xx Error Rate

**Symptoms:** `error_rate_5xx` in `/metrics` above threshold.

**Steps:**
1. `docker compose logs --tail=100 api` – identify repeated stack traces.
2. Check `/ready` to confirm dependency health.
3. If DB errors: follow §4.2.
4. If Ollama errors are causing 500s: follow §4.3 (or verify graceful fallback).
5. Review structured access logs for `"status_code": 5xx` entries and their `request_id`.

---

### 4.5 High API Latency

**Symptoms:** `latency_ms.p95` above threshold.

**Steps:**
1. Check `/metrics` for distribution. Is p99 also elevated?
2. If Ollama-path calls dominate: Ollama model inference is slow – expected under load.
3. Check `docker stats` for CPU/memory pressure.
4. Check DB query times: `docker compose exec postgres psql -U jarvis -c "SELECT * FROM pg_stat_activity;"`.
5. Restart the slow dependency service.

---

## 5. Backup and Restore

### 5.1 Backup PostgreSQL

```bash
docker compose exec postgres pg_dump -U jarvis jarvis > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 5.2 Restore PostgreSQL

```bash
docker compose exec -T postgres psql -U jarvis jarvis < backup_YYYYMMDD_HHMMSS.sql
```

Retain at least **7 daily backups**. Recovery Point Objective (RPO): ≤ 24 h.
Recovery Time Objective (RTO): ≤ 4 h.

---

## 6. Structured Log Correlation

All requests emit two JSON log lines – `request_started` and `request_finished` –
each containing a `request_id` UUID.

Example:
```json
{"event": "request_started", "request_id": "4a3b…", "method": "POST", "path": "/assistant/message"}
{"event": "request_finished", "request_id": "4a3b…", "method": "POST", "path": "/assistant/message", "status_code": 200, "duration_ms": 312.45}
```

To tail and filter logs for a specific request ID:
```bash
docker compose logs -f api | grep "4a3b…"
```

To tail only 5xx errors:
```bash
docker compose logs -f api | grep '"status_code": 5'
```

---

## 7. Escalation

For a single-user private deployment there is no external escalation path.
Document incidents in `INCIDENT_LOG.md` with:
- Timestamp (UTC)
- Symptom observed
- Affected endpoints
- Root cause
- Resolution steps taken
- Duration of impact
