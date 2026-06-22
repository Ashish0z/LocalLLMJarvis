import os
from pathlib import Path

db_path = Path("test_jarvis_api.db")
if db_path.exists():
    db_path.unlink()

os.environ["DATABASE_URL"] = "sqlite:///./test_jarvis_api.db"
os.environ["JARVIS_API_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


HEADERS = {"X-API-Key": "test-key"}


def teardown_module() -> None:
    if db_path.exists():
        db_path.unlink()


def test_health_is_public() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_today_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.get("/today")

    assert response.status_code == 401


def test_assistant_creates_task_and_today_returns_it() -> None:
    with TestClient(app) as client:
        capture = client.post(
            "/assistant/message",
            headers=HEADERS,
            json={
                "text": "Add a task to submit the insurance form tomorrow morning",
                "source": "chat",
            },
        )
        today = client.get("/today", headers=HEADERS)

    assert capture.status_code == 200
    assert capture.json()["actions"][0]["type"] == "task_created"
    assert today.status_code == 200
    assert today.json()["top_priorities"][0]["title"] == "submit the insurance form tomorrow morning"


def test_document_upload_and_ask() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("plan.md", b"The launch task is to test reminders.", "text/markdown")},
        )
        document_id = upload.json()["id"]
        answer = client.post(
            f"/documents/{document_id}/ask",
            headers=HEADERS,
            json={"question": "What is the launch task?"},
        )

    assert upload.status_code == 201
    assert answer.status_code == 200
    assert "test reminders" in " ".join(answer.json()["context_chunks"])
