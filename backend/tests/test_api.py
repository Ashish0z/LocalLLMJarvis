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


# ---------- Projects Engine ----------

def test_create_project_returns_201_with_milestones() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/projects",
            headers=HEADERS,
            json={
                "title": "Launch mobile app",
                "objective": "Ship the v1 mobile app to the App Store",
                "constraints": "Budget: $10k, team of 2",
                "deadline": "2025-12-31T00:00:00Z",
                "milestones": [
                    {"title": "Design", "sequence_order": 1},
                    {"title": "Development", "sequence_order": 2},
                    {"title": "QA and launch", "sequence_order": 3},
                ],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Launch mobile app"
    assert data["status"] == "planned"
    assert data["replan_notes"] is None
    assert len(data["milestones"]) == 3
    assert data["milestones"][0]["title"] == "Design"
    assert data["milestones"][0]["status"] == "planned"


def test_list_projects_and_filter_by_status() -> None:
    with TestClient(app) as client:
        project_id = client.post(
            "/projects",
            headers=HEADERS,
            json={"title": "Active project", "objective": "Get things done"},
        ).json()["id"]
        client.patch(
            f"/projects/{project_id}",
            headers=HEADERS,
            json={"status": "active"},
        )

        all_projects = client.get("/projects", headers=HEADERS)
        active_projects = client.get("/projects?status=active", headers=HEADERS)
        planned_projects = client.get("/projects?status=planned", headers=HEADERS)

    assert all_projects.status_code == 200
    active_ids = [p["id"] for p in active_projects.json()]
    assert project_id in active_ids
    planned_ids = [p["id"] for p in planned_projects.json()]
    assert project_id not in planned_ids


def test_get_project_includes_milestones() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/projects",
            headers=HEADERS,
            json={
                "title": "Research project",
                "objective": "Publish a paper",
                "milestones": [{"title": "Literature review", "sequence_order": 1}],
            },
        ).json()
        project_id = created["id"]
        fetched = client.get(f"/projects/{project_id}", headers=HEADERS)

    assert fetched.status_code == 200
    assert fetched.json()["id"] == project_id
    assert len(fetched.json()["milestones"]) == 1


def test_update_project_state_transitions() -> None:
    with TestClient(app) as client:
        project_id = client.post(
            "/projects",
            headers=HEADERS,
            json={"title": "State test project", "objective": "Test state transitions"},
        ).json()["id"]

        active = client.patch(f"/projects/{project_id}", headers=HEADERS, json={"status": "active"})
        blocked = client.patch(f"/projects/{project_id}", headers=HEADERS, json={"status": "blocked"})
        done = client.patch(f"/projects/{project_id}", headers=HEADERS, json={"status": "done"})

    assert active.json()["status"] == "active"
    assert blocked.json()["status"] == "blocked"
    assert done.json()["status"] == "done"


def test_add_and_update_milestone() -> None:
    with TestClient(app) as client:
        project_id = client.post(
            "/projects",
            headers=HEADERS,
            json={"title": "Milestone test", "objective": "Test milestones"},
        ).json()["id"]

        ms = client.post(
            f"/projects/{project_id}/milestones",
            headers=HEADERS,
            json={"title": "Phase 1", "sequence_order": 1},
        )
        milestone_id = ms.json()["id"]

        updated = client.patch(
            f"/projects/{project_id}/milestones/{milestone_id}",
            headers=HEADERS,
            json={"status": "active"},
        )

    assert ms.status_code == 201
    assert ms.json()["title"] == "Phase 1"
    assert updated.status_code == 200
    assert updated.json()["status"] == "active"


def test_replan_project_replaces_milestones_and_records_reason() -> None:
    with TestClient(app) as client:
        project_id = client.post(
            "/projects",
            headers=HEADERS,
            json={
                "title": "Replan test",
                "objective": "Test replanning flow",
                "milestones": [{"title": "Original phase", "sequence_order": 1}],
            },
        ).json()["id"]

        client.patch(f"/projects/{project_id}", headers=HEADERS, json={"status": "blocked"})

        replan = client.post(
            f"/projects/{project_id}/replan",
            headers=HEADERS,
            json={
                "reason": "Scope changed significantly",
                "updated_milestones": [
                    {"title": "Revised phase 1", "sequence_order": 1},
                    {"title": "Revised phase 2", "sequence_order": 2},
                ],
            },
        )

    assert replan.status_code == 200
    data = replan.json()
    assert data["replan_notes"] == "Scope changed significantly"
    assert data["status"] == "active"
    assert len(data["milestones"]) == 2
    assert data["milestones"][0]["title"] == "Revised phase 1"


def test_replan_without_updated_milestones_preserves_existing() -> None:
    with TestClient(app) as client:
        project_id = client.post(
            "/projects",
            headers=HEADERS,
            json={
                "title": "Replan preserve test",
                "objective": "Test milestone preservation on replan",
                "milestones": [{"title": "Keep me", "sequence_order": 1}],
            },
        ).json()["id"]

        replan = client.post(
            f"/projects/{project_id}/replan",
            headers=HEADERS,
            json={"reason": "Minor schedule slip"},
        )

    assert replan.status_code == 200
    data = replan.json()
    assert data["replan_notes"] == "Minor schedule slip"
    assert len(data["milestones"]) == 1
    assert data["milestones"][0]["title"] == "Keep me"


def test_project_not_found_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/projects/nonexistent-id", headers=HEADERS)

    assert response.status_code == 404
