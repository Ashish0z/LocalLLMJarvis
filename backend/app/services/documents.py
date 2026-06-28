import io
import json
import math
import re

from app.config import get_settings

try:
    import pypdf as _pypdf  # type: ignore[import-untyped]

    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False

try:
    import docx as _docx  # type: ignore[import-untyped]

    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


SUPPORTED_TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}
SUPPORTED_EXTENSIONS = {"txt", "md", "markdown", "csv", "json", "log"}

PDF_CONTENT_TYPES = {"application/pdf"}
PDF_EXTENSIONS = {"pdf"}

DOCX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
DOCX_EXTENSIONS = {"docx"}

VALID_PRIVACY_LABELS = {"public", "internal", "private"}
DEFAULT_PRIVACY_LABEL = "public"


def decode_document(filename: str, content_type: str | None, raw: bytes) -> str:
    settings = get_settings()
    if len(raw) > settings.max_document_bytes:
        raise ValueError(f"Document is larger than {settings.max_document_bytes} bytes")

    normalized_type = (content_type or "").split(";")[0].strip().lower()
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if extension in PDF_EXTENSIONS or normalized_type in PDF_CONTENT_TYPES:
        return _extract_pdf(raw)

    if extension in DOCX_EXTENSIONS or normalized_type in DOCX_CONTENT_TYPES:
        return _extract_docx(raw)

    supported_extension = extension in SUPPORTED_EXTENSIONS
    if normalized_type and normalized_type not in SUPPORTED_TEXT_TYPES and not supported_extension:
        raise ValueError(
            "Only text, markdown, csv, json, log, PDF, and DOCX files are supported"
        )

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        raise ValueError("Document has no readable text")
    return cleaned


def _extract_pdf(raw: bytes) -> str:
    if not _PYPDF_AVAILABLE:
        raise ValueError("PDF support requires the pypdf package")
    try:
        reader = _pypdf.PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(page.strip() for page in pages if page.strip())
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc
    if not text.strip():
        raise ValueError("PDF has no extractable text")
    return text


def _extract_docx(raw: bytes) -> str:
    if not _DOCX_AVAILABLE:
        raise ValueError("DOCX support requires the python-docx package")
    try:
        doc = _docx.Document(io.BytesIO(raw))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
    except Exception as exc:
        raise ValueError(f"Could not read DOCX: {exc}") from exc
    if not text.strip():
        raise ValueError("DOCX has no extractable text")
    return text


def summarize_text(text: str, max_chars: int = 500) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 120) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text.strip())
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def rank_chunks(question: str, chunks: list[str], limit: int = 4) -> list[str]:
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9]{3,}", question)}
    if not terms:
        return chunks[:limit]

    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        lowered = chunk.lower()
        score = sum(1 for term in terms if term in lowered)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for score, chunk in scored if score > 0][:limit]
    return selected or chunks[:limit]


def rank_chunks_with_indices(
    question: str, chunks: list[str], limit: int = 4
) -> list[tuple[int, str]]:
    """Like rank_chunks but returns ``(chunk_index, text)`` pairs."""
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9]{3,}", question)}
    if not terms:
        return list(enumerate(chunks))[:limit]

    scored: list[tuple[int, int, str]] = []
    for idx, chunk in enumerate(chunks):
        lowered = chunk.lower()
        score = sum(1 for term in terms if term in lowered)
        scored.append((score, idx, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [(idx, chunk) for score, idx, chunk in scored if score > 0][:limit]
    return selected or list(enumerate(chunks))[:limit]


# ---------------------------------------------------------------------------
# Semantic (embedding-based) helpers
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def semantic_rank_chunks(
    query_embedding: list[float],
    indexed_chunks: list[tuple[int, str, list[float] | None]],
    limit: int = 4,
) -> list[tuple[int, str]]:
    """Rank *(chunk_index, text, embedding)* triples by cosine similarity.

    Chunks without an embedding are given score 0 and appear last.
    Returns a list of ``(chunk_index, text)`` pairs ordered by relevance.
    """
    scored: list[tuple[float, int, str]] = []
    for idx, text, embedding in indexed_chunks:
        score = _cosine_similarity(query_embedding, embedding) if embedding is not None else 0.0
        scored.append((score, idx, text))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [(idx, text) for _score, idx, text in scored[:limit]]


def deserialize_embedding(raw: str | None) -> list[float] | None:
    """Deserialize a JSON-encoded embedding stored in the DB, or return None."""
    if raw is None:
        return None
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return value
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def serialize_embedding(embedding: list[float]) -> str:
    return json.dumps(embedding)

