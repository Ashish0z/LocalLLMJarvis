import io
import os
import struct
import zipfile
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
def test_document_upload_exposes_privacy_label() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("notes.txt", b"Meeting notes for Q3.", "text/plain")},
            data={"privacy_label": "internal"},
        )

    assert upload.status_code == 201
    assert upload.json()["privacy_label"] == "internal"


def test_document_upload_rejects_invalid_privacy_label() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("notes.txt", b"Some text.", "text/plain")},
            data={"privacy_label": "top_secret"},
        )

    assert upload.status_code == 400


def test_private_document_blocks_ask_and_content() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("secret.txt", b"Classified content.", "text/plain")},
            data={"privacy_label": "private"},
        )
        assert upload.status_code == 201
        doc_id = upload.json()["id"]

        ask_response = client.post(
            f"/documents/{doc_id}/ask",
            headers=HEADERS,
            json={"question": "What is the content?"},
        )
        detail_response = client.get(f"/documents/{doc_id}", headers=HEADERS)

    assert ask_response.status_code == 403
    assert detail_response.status_code == 403


def test_private_document_appears_in_list() -> None:
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
            files={"file": ("priv.txt", b"Private data.", "text/plain")},
            data={"privacy_label": "private"},
        )
        doc_id = upload.json()["id"]
        listing = client.get("/documents", headers=HEADERS)

    ids = [d["id"] for d in listing.json()]
    assert doc_id in ids


def test_ask_response_includes_citations() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("faq.txt", b"The sky is blue. Water is wet.", "text/plain")},
        )
        doc_id = upload.json()["id"]
        answer = client.post(
            f"/documents/{doc_id}/ask",
            headers=HEADERS,
            json={"question": "What color is the sky?"},
        )

    assert answer.status_code == 200
    body = answer.json()
    assert "citations" in body
    assert len(body["citations"]) > 0
    citation = body["citations"][0]
    assert citation["document_id"] == doc_id
    assert citation["filename"] == "faq.txt"
    assert "chunk_index" in citation
    assert "text" in citation


def _minimal_pdf(text: str) -> bytes:
    """Build a minimal valid single-page PDF containing *text*."""
    content_stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    stream_bytes = content_stream.encode()
    objects: list[str] = []

    def obj(n: int, body: str) -> str:
        return f"{n} 0 obj\n{body}\nendobj\n"

    objects.append(obj(1, "<< /Type /Catalog /Pages 2 0 R >>"))
    objects.append(obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    objects.append(
        obj(
            3,
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        )
    )
    objects.append(
        obj(
            4,
            f"<< /Length {len(stream_bytes)} >>\nstream\n{content_stream}\nendstream",
        )
    )
    objects.append(
        obj(
            5,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        )
    )

    header = b"%PDF-1.4\n"
    body_bytes = header
    offsets: list[int] = []
    for o in objects:
        offsets.append(len(body_bytes))
        body_bytes += o.encode()

    xref_offset = len(body_bytes)
    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    )
    return body_bytes + (xref + trailer).encode()


def _minimal_docx(text: str) -> bytes:
    """Build a minimal valid DOCX file containing *text*."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml"'
            ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1"'
            ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
            ' Target="word/document.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "word/_rels/document.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            "</Relationships>",
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"'
            ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
            "</w:body>"
            "</w:document>",
        )
    return buf.getvalue()


def test_pdf_document_upload() -> None:
    from app.services.documents import _PYPDF_AVAILABLE

    if not _PYPDF_AVAILABLE:
        return  # pragma: no cover

    pdf_bytes = _minimal_pdf("Quarterly revenue increased by fifteen percent")
    with TestClient(app) as client:
        upload = client.post(
            "/documents",
            headers=HEADERS,
            files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        )

    assert upload.status_code == 201
    assert upload.json()["filename"] == "report.pdf"


def test_docx_document_upload() -> None:
    from app.services.documents import _DOCX_AVAILABLE

    if not _DOCX_AVAILABLE:
        return  # pragma: no cover

    docx_bytes = _minimal_docx("Annual performance review summary")
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
            files={
                "file": (
                    "review.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert upload.status_code == 201
    assert upload.json()["filename"] == "review.docx"
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
