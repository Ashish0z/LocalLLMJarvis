"""Unit tests for app/services/documents.py."""

import math

import pytest

from app.services.documents import (
    DEFAULT_PRIVACY_LABEL,
    VALID_PRIVACY_LABELS,
    _cosine_similarity,
    _extract_docx,
    _extract_pdf,
    chunk_text,
    decode_document,
    deserialize_embedding,
    rank_chunks,
    rank_chunks_with_indices,
    semantic_rank_chunks,
    serialize_embedding,
    summarize_text,
)


# ---------------------------------------------------------------------------
# decode_document
# ---------------------------------------------------------------------------


def test_decode_plain_text() -> None:
    text = decode_document("notes.txt", "text/plain", b"Hello world")
    assert text == "Hello world"


def test_decode_normalises_crlf() -> None:
    text = decode_document("a.txt", "text/plain", b"line1\r\nline2\r\n")
    assert "\r" not in text
    assert "line1\nline2" == text


def test_decode_rejects_oversized_file(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config as cfg

    monkeypatch.setattr(cfg.get_settings(), "max_document_bytes", 10)
    with pytest.raises(ValueError, match="larger than"):
        decode_document("big.txt", "text/plain", b"x" * 11)


def test_decode_rejects_unknown_type() -> None:
    with pytest.raises(ValueError):
        decode_document("file.xyz", "application/octet-stream", b"binary stuff")


def test_decode_empty_text_raises() -> None:
    with pytest.raises(ValueError, match="no readable text"):
        decode_document("empty.txt", "text/plain", b"   ")


def test_decode_pdf_unsupported_raises_when_pypdf_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.documents as svc

    monkeypatch.setattr(svc, "_PYPDF_AVAILABLE", False)
    with pytest.raises(ValueError, match="pypdf"):
        decode_document("file.pdf", "application/pdf", b"%PDF-1.4")


def test_decode_docx_unsupported_raises_when_docx_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.documents as svc

    monkeypatch.setattr(svc, "_DOCX_AVAILABLE", False)
    with pytest.raises(ValueError, match="python-docx"):
        decode_document(
            "file.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"PK\x03\x04",
        )


# ---------------------------------------------------------------------------
# summarize_text
# ---------------------------------------------------------------------------


def test_summarize_short_text_unchanged() -> None:
    text = "Short note."
    assert summarize_text(text, max_chars=100) == text


def test_summarize_long_text_truncated() -> None:
    text = "word " * 200
    result = summarize_text(text, max_chars=50)
    assert len(result) <= 50
    assert result.endswith("...")


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------


def test_chunk_text_single_short() -> None:
    chunks = chunk_text("Hello world", chunk_size=100, overlap=10)
    assert chunks == ["Hello world"]


def test_chunk_text_overlap() -> None:
    text = "a" * 100
    chunks = chunk_text(text, chunk_size=60, overlap=20)
    assert len(chunks) >= 2
    # Overlap means consecutive chunks share content
    assert chunks[0][-20:] in chunks[1] or chunks[1][:20] in chunks[0]


def test_chunk_text_empty_input() -> None:
    assert chunk_text("") == []


# ---------------------------------------------------------------------------
# rank_chunks / rank_chunks_with_indices
# ---------------------------------------------------------------------------


def test_rank_chunks_returns_relevant_first() -> None:
    chunks = ["The sky is blue", "Dogs are cute", "Blue whales are large"]
    ranked = rank_chunks("sky blue", chunks)
    assert "The sky is blue" == ranked[0]


def test_rank_chunks_with_indices_returns_tuples() -> None:
    chunks = ["alpha beta", "gamma delta", "alpha gamma"]
    pairs = rank_chunks_with_indices("alpha", chunks)
    indices = [idx for idx, _ in pairs]
    assert 0 in indices  # "alpha beta" should be selected
    assert 2 in indices  # "alpha gamma" should be selected


def test_rank_chunks_no_terms_returns_first_n() -> None:
    chunks = ["one", "two", "three", "four", "five"]
    assert rank_chunks("", chunks, limit=3) == ["one", "two", "three"]


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def test_cosine_identical_vectors() -> None:
    v = [1.0, 2.0, 3.0]
    assert math.isclose(_cosine_similarity(v, v), 1.0, rel_tol=1e-9)


def test_cosine_orthogonal_vectors() -> None:
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert math.isclose(_cosine_similarity(a, b), 0.0, abs_tol=1e-9)


def test_cosine_zero_vector_returns_zero() -> None:
    assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


# ---------------------------------------------------------------------------
# semantic_rank_chunks
# ---------------------------------------------------------------------------


def test_semantic_rank_ranks_by_similarity() -> None:
    q = [1.0, 0.0]
    chunks = [
        (0, "irrelevant chunk", [0.0, 1.0]),   # orthogonal — low score
        (1, "matching chunk", [0.9, 0.1]),      # close to query — high score
    ]
    ranked = semantic_rank_chunks(q, chunks, limit=2)
    assert ranked[0][0] == 1  # "matching chunk" should be first


def test_semantic_rank_none_embedding_falls_to_end() -> None:
    q = [1.0, 0.0]
    chunks = [
        (0, "no embedding", None),
        (1, "has embedding", [1.0, 0.0]),
    ]
    ranked = semantic_rank_chunks(q, chunks, limit=2)
    assert ranked[0][0] == 1  # chunk with embedding should rank higher


# ---------------------------------------------------------------------------
# Embedding serialization round-trip
# ---------------------------------------------------------------------------


def test_embedding_serialization_round_trip() -> None:
    original = [0.1, 0.2, 0.3, -0.5]
    serialized = serialize_embedding(original)
    restored = deserialize_embedding(serialized)
    assert restored is not None
    assert all(math.isclose(a, b) for a, b in zip(original, restored))


def test_deserialize_none_returns_none() -> None:
    assert deserialize_embedding(None) is None


def test_deserialize_invalid_json_returns_none() -> None:
    assert deserialize_embedding("not-json") is None


# ---------------------------------------------------------------------------
# Privacy label constants
# ---------------------------------------------------------------------------


def test_valid_privacy_labels_set() -> None:
    assert "public" in VALID_PRIVACY_LABELS
    assert "private" in VALID_PRIVACY_LABELS
    assert "internal" in VALID_PRIVACY_LABELS


def test_default_privacy_label_is_public() -> None:
    assert DEFAULT_PRIVACY_LABEL == "public"
