# Complete Local LLM Jarvis Setup

This guide walks from a fresh machine to a working private assistant stack:

- Docker backend with FastAPI, Postgres, Ollama, and the web companion.
- Tailscale private-network access.
- Android app setup and APK creation.

The commands below assume Windows PowerShell from the repository root:

```powershell
cd C:\Users\user\Documents\LocalLLMJarvis
```

## 1. Install Base Requirements

Install these first:

- Git.
- Docker Desktop.
- Tailscale on the server machine.
- Tailscale on the Android phone.
- Android Studio.
- Java JDK. Android Studio usually manages the Android build JDK itself.

Optional but useful:

- Python 3.12 for local backend checks outside Docker.
- Node.js 22 if running the web app outside Docker.

After installing Docker Desktop, open it once and make sure the Docker engine is running.

Check Docker:

```powershell
docker --version
docker compose version
```

Check Tailscale:

```powershell
tailscale status
```

If `tailscale` is not available in PowerShell, open the Tailscale desktop app and sign in there.

## 2. Configure Environment

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Default `.env` values are enough for local Docker development:

```env
DATABASE_URL=postgresql+psycopg://jarvis:jarvis@postgres:5432/jarvis
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

For first setup, keep the default database credentials. Change them before storing sensitive personal data.

## 3. Start the Docker Stack

Build and start all services:

```powershell
docker compose up --build
```

Open another PowerShell window for follow-up commands.

Check containers:

```powershell
docker compose ps
```

Expected services:

- `api`
- `web`
- `postgres`
- `ollama`

## 4. Pull the Ollama Model

The `ollama` container starts empty unless a model already exists in its Docker volume.

Pull the configured model:

```powershell
docker compose exec ollama ollama pull llama3.1:8b
```

List available models:

```powershell
docker compose exec ollama ollama list
```

If your machine has limited RAM, use a smaller model and update `.env`:

```env
OLLAMA_MODEL=llama3.2:3b
```

Then restart the API:

```powershell
docker compose restart api
```

## 5. Verify Backend and Web

Open:

- API docs: `http://localhost:8000/docs`
- Web companion: `http://localhost:5173`
- Ollama API: `http://localhost:11434`

Check API health:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Create a test task:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/assistant/message `
  -ContentType "application/json" `
  -Body '{"text":"Add a task to submit the insurance form tomorrow morning","source":"web"}'
```

Load the Today view:

```powershell
Invoke-RestMethod http://localhost:8000/today
```

## 6. Postgres Database Setup

Postgres runs inside Docker using the `postgres_data` Docker volume.

Connection details inside Docker:

- Host: `postgres`
- Port: `5432`
- Database: `jarvis`
- User: `jarvis`
- Password: `jarvis`

Connection details from the host machine:

- Host: `localhost`
- Port: `5432`
- Database: `jarvis`
- User: `jarvis`
- Password: `jarvis`

Open `psql` inside the container:

```powershell
docker compose exec postgres psql -U jarvis -d jarvis
```

List tables:

```sql
\dt
```

Exit:

```sql
\q
```

Back up the database:

```powershell
docker compose exec postgres pg_dump -U jarvis jarvis > jarvis_backup.sql
```

Restore from a backup:

```powershell
Get-Content .\jarvis_backup.sql | docker compose exec -T postgres psql -U jarvis -d jarvis
```

## 7. Tailscale Private Network Setup

Install and sign in to Tailscale on:

- The machine running Docker.
- The Android phone.

On the server machine, confirm it is connected:

```powershell
tailscale status
tailscale ip -4
```

You can use either:

- The Tailscale IP, such as `http://100.x.y.z:8000`.
- The MagicDNS hostname, such as `http://your-machine-name:8000`.

From the Android phone:

1. Connect Tailscale.
2. Make sure the phone is in the same tailnet.
3. Open the Android app.
4. In Settings, set the API URL to the server's Tailscale address.

Examples:

```text
http://100.x.y.z:8000
http://your-machine-name:8000
```

Security notes:

- The current Docker Compose file publishes ports on the host for easy MVP testing.
- Keep the host firewall enabled.
- Prefer Tailscale addresses from the Android app.
- Before storing sensitive personal data, change default Postgres credentials and review firewall access.

## 8. Build the Android APK

Open Android Studio:

1. Choose `File > Open`.
2. Open `C:\Users\user\Documents\LocalLLMJarvis\android`.
3. Let Gradle sync finish.
4. Connect an Android device or start an emulator.

Run the app:

1. Select the `app` run configuration.
2. Click Run.

Create a debug APK:

1. In Android Studio, select `Build > Build Bundle(s) / APK(s) > Build APK(s)`.
2. After the build finishes, click `locate`.
3. The debug APK is usually under:

```text
android\app\build\outputs\apk\debug\app-debug.apk
```

Create a signed release APK:

1. Select `Build > Generate Signed Bundle / APK`.
2. Choose `APK`.
3. Create or select a keystore.
4. Choose the `release` variant.
5. Finish the wizard.

Keep the keystore safe. Losing it means future app updates cannot use the same signing identity.

## 9. Android API URL Choices

Use this URL on the Android Emulator:

```text
http://10.0.2.2:8000
```

Use this pattern on a physical phone over Tailscale:

```text
http://100.x.y.z:8000
```

or:

```text
http://your-machine-name:8000
```

## 10. Stop and Restart

Stop services:

```powershell
docker compose down
```

Stop services and remove local Docker volumes:

```powershell
docker compose down -v
```

Only use `-v` when you are comfortable deleting the local Postgres and Ollama data volumes.

Restart after code changes:

```powershell
docker compose up --build
```

## 11. Secure Transport

All traffic between clients and the backend should be encrypted. Two supported approaches are described below.

### Option A — Tailscale (recommended for personal use)

Tailscale creates a private WireGuard mesh between your devices. All traffic inside the tailnet is encrypted end-to-end and requires no certificate management.

1. Install Tailscale on the server machine and sign in.
2. Install Tailscale on every client device (Android phone, laptop, etc.).
3. Add each device to the same tailnet in the Tailscale admin console.
4. Set the Android/web API URL to the server's Tailscale address:

```text
http://100.x.y.z:8000
http://your-machine-name:8000
```

5. Keep host firewall rules in place so port 8000 is only reachable from the Tailscale interface, not the public internet:

```powershell
# Windows example: allow 8000 only from Tailscale subnet 100.64.0.0/10
New-NetFirewallRule -DisplayName "Jarvis API Tailscale" -Direction Inbound -Protocol TCP -LocalPort 8000 -RemoteAddress "100.64.0.0/10" -Action Allow
```

### Option B — Reverse proxy with TLS (HTTPS)

Place a TLS-terminating reverse proxy in front of the API container. Two common choices are shown below.

**Caddy** (automatic certificates via Let's Encrypt):

```text
jarvis.example.com {
    reverse_proxy localhost:8000
}
```

Run with `caddy run --config Caddyfile`.

**nginx** (with certificates from Certbot):

```nginx
server {
    listen 443 ssl;
    server_name jarvis.example.com;
    ssl_certificate     /etc/letsencrypt/live/jarvis.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jarvis.example.com/privkey.pem;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

When using a reverse proxy, update `API_CORS_ORIGINS` in `.env` to your HTTPS domain and set `APP_ENV=production` so the backend enforces the stricter security rules.

### Logging and sensitive data

The backend applies a sanitizing log filter at startup. Log lines containing `X-API-Key`, `Authorization`, or `JARVIS_API_KEY` values are automatically redacted before they reach any log sink. No other PII filtering is applied at this time; avoid logging user message content at `INFO` level or above.

## 12. Next Implementation Steps

Recommended next work:

- Add Android notification and alarm scheduling.
- Add database migrations with Alembic.
- Add authentication for private clients.
- Add Health Connect ingestion.
- Add Calendar integration.

Standout feature modules to implement after the baseline:

- Projects engine (objective -> milestones -> timeline -> tasks).
- Goals engine (baseline interview -> phased plan -> adaptive reminders).
- Habits engine (build/remove plans -> streaks -> accountability).
- Automation engine (memory-driven project/goal/habit suggestions).
- Tracking dashboard service (daily/weekly metrics and retrospective summaries).
- Add document upload and indexing.
- Add release signing config documentation once a keystore strategy is chosen.

