from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth import require_api_key
from app.config import get_settings
from app.database import init_db
from app.limiter import limiter
from app.routers import assistant, documents, logs, memory, reminders, tasks, today

settings = get_settings()

app = FastAPI(
    title="Local LLM Jarvis API",
    version="0.1.0",
    description="Local-first personal assistant API for Android and web clients.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)
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
    return {"status": "ok", "environment": settings.app_env}


protected_dependencies = [Depends(require_api_key)]
app.include_router(today.router, dependencies=protected_dependencies)
app.include_router(assistant.router, dependencies=protected_dependencies)
app.include_router(tasks.router, dependencies=protected_dependencies)
app.include_router(reminders.router, dependencies=protected_dependencies)
app.include_router(logs.router, dependencies=protected_dependencies)
app.include_router(memory.router, dependencies=protected_dependencies)
app.include_router(documents.router, dependencies=protected_dependencies)
