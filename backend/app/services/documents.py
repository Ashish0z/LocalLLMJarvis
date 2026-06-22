import re

from app.config import get_settings


SUPPORTED_TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}


def decode_document(filename: str, content_type: str | None, raw: bytes) -> str:
    settings = get_settings()
    if len(raw) > settings.max_document_bytes:
        raise ValueError(f"Document is larger than {settings.max_document_bytes} bytes")

    normalized_type = (content_type or "").split(";")[0].strip().lower()
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    supported_extension = extension in {"txt", "md", "markdown", "csv", "json", "log"}
    if normalized_type and normalized_type not in SUPPORTED_TEXT_TYPES and not supported_extension:
        raise ValueError("Only text, markdown, csv, json, and log files are supported in this MVP")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        raise ValueError("Document has no readable text")
    return cleaned


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

