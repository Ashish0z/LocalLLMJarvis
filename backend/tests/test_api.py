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
