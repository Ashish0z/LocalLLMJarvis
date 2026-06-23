from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_api_key
from app.config import get_settings
from app.database import init_db
from app.routers import assistant, documents, logs, memory, projects, reminders, tasks, today

settings = get_settings()

app = FastAPI(
    title="Local LLM Jarvis API",
    version="0.1.0",
    description="Local-first personal assistant API for Android and web clients.",
)

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
app.include_router(projects.router, dependencies=protected_dependencies)
