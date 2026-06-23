import httpx
from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth import require_api_key
from app.config import get_settings
from app.database import init_db, engine
from app.middleware import RequestLoggingMiddleware, metrics_store
from app.routers import assistant, documents, logs, memory, reminders, tasks, today

settings = get_settings()

app = FastAPI(
    title="Local LLM Jarvis API",
    version="0.1.0",
    description="Local-first personal assistant API for Android and web clients.",
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness probe – returns ok if the process is running."""
    return {"status": "ok", "environment": settings.app_env}


@app.get("/ready", tags=["system"])
async def ready() -> dict:
    """Readiness probe – checks DB and Ollama connectivity."""
    checks: dict[str, dict] = {}

    # --- Database ---
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}

    # --- Ollama (optional dependency) ---
    ollama_url = f"{str(settings.ollama_base_url).rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(ollama_url)
            resp.raise_for_status()
        checks["ollama"] = {"status": "ok"}
    except Exception as exc:
        checks["ollama"] = {"status": "unavailable", "detail": str(exc)}

    overall = "ok" if checks["database"]["status"] == "ok" else "degraded"
    status_code = 200 if overall == "ok" else 503

    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={"status": overall, "checks": checks},
        status_code=status_code,
    )


@app.get("/metrics", tags=["system"])
def metrics() -> dict:
    """Basic in-process metrics: request counts, error rates, and latency percentiles."""
    return metrics_store.snapshot()


protected_dependencies = [Depends(require_api_key)]
app.include_router(today.router, dependencies=protected_dependencies)
app.include_router(assistant.router, dependencies=protected_dependencies)
app.include_router(tasks.router, dependencies=protected_dependencies)
app.include_router(reminders.router, dependencies=protected_dependencies)
app.include_router(logs.router, dependencies=protected_dependencies)
app.include_router(memory.router, dependencies=protected_dependencies)
app.include_router(documents.router, dependencies=protected_dependencies)
