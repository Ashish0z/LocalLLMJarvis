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


# ---------------------------------------------------------------------------
# System / health
# ---------------------------------------------------------------------------


def test_health_is_public() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_today_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.get("/today")

    assert response.status_code == 401


def test_invalid_api_key_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/today", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Assistant + Today
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tasks router
# ---------------------------------------------------------------------------


def test_create_task_happy_path() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/tasks",
            headers=HEADERS,
            json={"title": "Write unit tests", "source": "web"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Write unit tests"
    assert data["status"] == "pending"
    assert "id" in data


def test_create_task_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.post("/tasks", json={"title": "Unauthorised task"})

    assert response.status_code == 401


def test_list_tasks() -> None:
    with TestClient(app) as client:
        client.post("/tasks", headers=HEADERS, json={"title": "List test task"})
        response = client.get("/tasks", headers=HEADERS)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(t["title"] == "List test task" for t in response.json())


def test_update_task_happy_path() -> None:
    with TestClient(app) as client:
        create = client.post(
            "/tasks",
            headers=HEADERS,
            json={"title": "Task to complete"},
        )
        task_id = create.json()["id"]
        update = client.patch(
            f"/tasks/{task_id}",
            headers=HEADERS,
            json={"status": "done"},
        )

    assert update.status_code == 200
    assert update.json()["status"] == "done"


def test_update_task_not_found() -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/tasks/nonexistent-id",
            headers=HEADERS,
            json={"status": "done"},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Reminders router
# ---------------------------------------------------------------------------


def test_create_reminder_happy_path() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/reminders",
            headers=HEADERS,
            json={"title": "Take medication", "source": "web"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Take medication"
    assert data["status"] == "active"
    assert "id" in data


def test_create_reminder_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.post("/reminders", json={"title": "Unauthorised reminder"})

    assert response.status_code == 401


def test_list_reminders() -> None:
    with TestClient(app) as client:
        client.post("/reminders", headers=HEADERS, json={"title": "List test reminder"})
        response = client.get("/reminders", headers=HEADERS)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(r["title"] == "List test reminder" for r in response.json())


def test_update_reminder_happy_path() -> None:
    with TestClient(app) as client:
        create = client.post(
            "/reminders",
            headers=HEADERS,
            json={"title": "Reminder to cancel"},
        )
        reminder_id = create.json()["id"]
        update = client.patch(
            f"/reminders/{reminder_id}",
            headers=HEADERS,
            json={"status": "cancelled"},
        )

    assert update.status_code == 200
    assert update.json()["status"] == "cancelled"


def test_update_reminder_not_found() -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/reminders/nonexistent-id",
            headers=HEADERS,
            json={"status": "done"},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Logs router
# ---------------------------------------------------------------------------


def test_create_water_log() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/logs/water",
            headers=HEADERS,
            json={"amount": 300, "unit": "ml"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "water"
    assert data["amount"] == 300


def test_create_nutrition_log() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/logs/nutrition",
            headers=HEADERS,
            json={"value": "oatmeal with berries"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "nutrition"
    assert data["value"] == "oatmeal with berries"


def test_create_generic_log() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/logs",
            headers=HEADERS,
            json={"kind": "sleep", "value": "7h30m"},
        )

    assert response.status_code == 200
    assert response.json()["kind"] == "sleep"


def test_list_logs() -> None:
    with TestClient(app) as client:
        client.post("/logs/water", headers=HEADERS, json={"amount": 200, "unit": "ml"})
        response = client.get("/logs", headers=HEADERS)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_logs_filter_by_kind() -> None:
    with TestClient(app) as client:
        client.post("/logs/water", headers=HEADERS, json={"amount": 100, "unit": "ml"})
        response = client.get("/logs?kind=water", headers=HEADERS)

    assert response.status_code == 200
    assert all(entry["kind"] == "water" for entry in response.json())


def test_create_log_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.post("/logs/water", json={"amount": 250})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Memory router
# ---------------------------------------------------------------------------


def test_create_memory_happy_path() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/memory",
            headers=HEADERS,
            json={"category": "preference", "content": "I prefer morning workouts."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "preference"
    assert data["content"] == "I prefer morning workouts."
    assert data["is_active"] is True
    assert "id" in data


def test_create_memory_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/memory",
            json={"category": "pref", "content": "Unauthorised"},
        )

    assert response.status_code == 401


def test_list_memory() -> None:
    with TestClient(app) as client:
        client.post(
            "/memory",
            headers=HEADERS,
            json={"category": "fact", "content": "Likes tea."},
        )
        response = client.get("/memory", headers=HEADERS)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(m["content"] == "Likes tea." for m in response.json())


def test_update_memory_happy_path() -> None:
    with TestClient(app) as client:
        create = client.post(
            "/memory",
            headers=HEADERS,
            json={"category": "pref", "content": "Old content"},
        )
        memory_id = create.json()["id"]
        update = client.patch(
            f"/memory/{memory_id}",
            headers=HEADERS,
            json={"content": "Updated content"},
        )

    assert update.status_code == 200
    assert update.json()["content"] == "Updated content"


def test_update_memory_not_found() -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/memory/nonexistent-id",
            headers=HEADERS,
            json={"content": "Should not exist"},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Documents router – upload / retrieval integration
# ---------------------------------------------------------------------------


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


def test_document_upload_requires_api_key() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            files={"file": ("note.txt", b"Some text", "text/plain")},
        )

    assert response.status_code == 401


def test_document_upload_unsupported_type_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("image.png", b"\x89PNG\r\n", "image/png")},
        )

    assert response.status_code == 400


def test_document_list() -> None:
    with TestClient(app) as client:
        client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("list_test.txt", b"Contents for listing.", "text/plain")},
        )
        response = client.get("/documents", headers=HEADERS)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(d["filename"] == "list_test.txt" for d in response.json())


def test_document_get_by_id() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("get_test.txt", b"Retrievable content.", "text/plain")},
        )
        document_id = upload.json()["id"]
        response = client.get(f"/documents/{document_id}", headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["filename"] == "get_test.txt"
    assert "text" in response.json()


def test_document_get_not_found() -> None:
    with TestClient(app) as client:
        response = client.get("/documents/nonexistent-id", headers=HEADERS)

    assert response.status_code == 404


def test_document_delete_lifecycle() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("delete_test.txt", b"Delete me.", "text/plain")},
        )
        document_id = upload.json()["id"]
        delete = client.delete(f"/documents/{document_id}", headers=HEADERS)
        after_delete = client.get(f"/documents/{document_id}", headers=HEADERS)

    assert upload.status_code == 201
    assert delete.status_code == 204
    assert after_delete.status_code == 404


def test_document_delete_not_found() -> None:
    with TestClient(app) as client:
        response = client.delete("/documents/nonexistent-id", headers=HEADERS)

    assert response.status_code == 404


def test_document_ask_not_found() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents/nonexistent-id/ask",
            headers=HEADERS,
            json={"question": "Any question?"},
        )

    assert response.status_code == 404
