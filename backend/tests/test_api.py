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


def test_habit_crud_and_streak_tracking() -> None:
    with TestClient(app) as client:
        create = client.post(
            "/habits",
            headers=HEADERS,
            json={"title": "Morning run", "mode": "build", "frequency": "daily"},
        )
        assert create.status_code == 201
        habit = create.json()
        habit_id = habit["id"]
        assert habit["mode"] == "build"
        assert habit["current_streak"] == 0
        assert habit["longest_streak"] == 0

        checkin1 = client.post(
            f"/habits/{habit_id}/checkins",
            headers=HEADERS,
            json={"outcome": "complete"},
        )
        assert checkin1.status_code == 201
        assert checkin1.json()["outcome"] == "complete"

        checkin2 = client.post(
            f"/habits/{habit_id}/checkins",
            headers=HEADERS,
            json={"outcome": "complete"},
        )
        assert checkin2.status_code == 201

        updated = client.get("/habits", headers=HEADERS)
        assert updated.status_code == 200
        record = next(h for h in updated.json() if h["id"] == habit_id)
        assert record["current_streak"] == 2
        assert record["longest_streak"] == 2

        relapse = client.post(
            f"/habits/{habit_id}/checkins",
            headers=HEADERS,
            json={"outcome": "relapse", "notes": "skipped gym"},
        )
        assert relapse.status_code == 201

        after_relapse = client.get("/habits", headers=HEADERS)
        record2 = next(h for h in after_relapse.json() if h["id"] == habit_id)
        assert record2["current_streak"] == 0
        assert record2["longest_streak"] == 2
        assert record2["relapse_count"] == 1

        checkins = client.get(f"/habits/{habit_id}/checkins", headers=HEADERS)
        assert checkins.status_code == 200
        assert len(checkins.json()) == 3

        patch = client.patch(
            f"/habits/{habit_id}",
            headers=HEADERS,
            json={"coaching_tone": "strict"},
        )
        assert patch.status_code == 200
        assert patch.json()["coaching_tone"] == "strict"


def test_habit_checkin_404_for_unknown_habit() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/habits/nonexistent-id/checkins",
            headers=HEADERS,
            json={"outcome": "complete"},
        )
    assert response.status_code == 404


def test_goal_crud_interview_and_checkins() -> None:
    with TestClient(app) as client:
        create = client.post(
            "/goals",
            headers=HEADERS,
            json={"title": "Run a sub-20 minute 5K", "description": "Fitness goal"},
        )
        assert create.status_code == 201
        goal = create.json()
        goal_id = goal["id"]
        assert goal["status"] == "active"
        assert goal["baseline_data"] is None

        interview = client.post(
            f"/goals/{goal_id}/interview",
            headers=HEADERS,
            json={
                "current_level": "beginner",
                "available_time": "30 minutes daily",
                "constraints": "knee injury",
                "motivation_style": "data-driven",
            },
        )
        assert interview.status_code == 200
        assert interview.json()["baseline_data"] is not None

        checkin = client.post(
            f"/goals/{goal_id}/checkins",
            headers=HEADERS,
            json={"notes": "Completed week 1 training", "adherence_rating": 4},
        )
        assert checkin.status_code == 201
        assert checkin.json()["adherence_rating"] == 4

        checkins = client.get(f"/goals/{goal_id}/checkins", headers=HEADERS)
        assert checkins.status_code == 200
        assert len(checkins.json()) == 1

        patch = client.patch(
            f"/goals/{goal_id}",
            headers=HEADERS,
            json={"current_phase": "week-2", "status": "active"},
        )
        assert patch.status_code == 200
        assert patch.json()["current_phase"] == "week-2"

        complete = client.patch(
            f"/goals/{goal_id}",
            headers=HEADERS,
            json={"status": "completed"},
        )
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"

        goals_list = client.get("/goals?status=active", headers=HEADERS)
        assert all(g["id"] != goal_id for g in goals_list.json())


def test_goal_404_for_unknown_goal() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/goals/nonexistent-id/interview",
            headers=HEADERS,
            json={"current_level": "beginner"},
        )
    assert response.status_code == 404


def test_assistant_creates_habit_from_message() -> None:
    with TestClient(app) as client:
        result = client.post(
            "/assistant/message",
            headers=HEADERS,
            json={"text": "I want to build a habit to meditate every morning", "source": "chat"},
        )
    assert result.status_code == 200
    actions = result.json()["actions"]
    assert any(a["type"] == "habit_created" for a in actions)


def test_assistant_creates_goal_from_message() -> None:
    with TestClient(app) as client:
        result = client.post(
            "/assistant/message",
            headers=HEADERS,
            json={"text": "My goal is to learn guitar basics in 90 days", "source": "chat"},
        )
    assert result.status_code == 200
    actions = result.json()["actions"]
    assert any(a["type"] == "goal_created" for a in actions)
