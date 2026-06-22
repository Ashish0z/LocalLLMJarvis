# Web Companion Setup

This directory contains the MVP web companion.

The web app is secondary to Android. It provides:

- Quick capture.
- Today view.
- A basic browser surface for future document workflows.

## Run with Docker

From the repository root:

```powershell
docker compose up --build web api postgres ollama
```

Open:

```text
http://localhost:5173
```

The web container uses:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Run Locally without Docker

Install Node.js 22 or newer, then from this directory:

```powershell
cd web
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

If the backend is on another machine, set the API URL before starting Vite:

```powershell
$env:VITE_API_BASE_URL = "http://100.x.y.z:8000"
npm run dev
```

## Backend Requirement

The web app expects the backend API to be available.

Start the backend stack first:

```powershell
docker compose up --build api postgres ollama
```

Check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## Tailscale Use

For access from another device on the tailnet:

1. Start the Docker stack on the server.
2. Confirm the server has a Tailscale IP:

   ```powershell
   tailscale ip -4
   ```

3. Open the web app with the server address:

   ```text
   http://100.x.y.z:5173
   ```

For a more locked-down deployment, keep browser use on the server machine or add a reverse proxy/Tailscale Serve setup later.

## Future Web Work

Planned additions:

- Document upload.
- Document Q&A.
- File task extraction.
- Memory management.
- Calendar and Notion integration settings.

