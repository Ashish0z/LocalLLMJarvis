from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.documents import (
    DEFAULT_PRIVACY_LABEL,
    VALID_PRIVACY_LABELS,
    chunk_text,
    decode_document,
    deserialize_embedding,
    rank_chunks_with_indices,
    semantic_rank_chunks,
    serialize_embedding,
    summarize_text,
)
from app.limiter import limiter
from app.services.documents import chunk_text, decode_document, rank_chunks, summarize_text
from app.services.ollama import OllamaClient

router = APIRouter(prefix="/documents", tags=["documents"])
ollama = OllamaClient()


def _enforce_privacy(document: models.Document, action: str) -> None:
    """Raise 403 when *document*'s privacy label blocks *action*.

    * ``private``  – blocks ``read_content`` (full text) and ``ask``
    * ``internal`` – no extra restriction (content is accessible to any
      authenticated caller, which is already enforced by the API-key middleware)
    * ``public``   – no restriction
    """
    if document.privacy_label == "private" and action in {"read_content", "ask"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This document is private; its content cannot be retrieved.",
        )


@router.post("", response_model=schemas.DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    privacy_label: str = Form(default=DEFAULT_PRIVACY_LABEL),
    db: Session = Depends(get_db),
) -> models.Document:
    if privacy_label not in VALID_PRIVACY_LABELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid privacy_label '{privacy_label}'. "
            f"Must be one of: {', '.join(sorted(VALID_PRIVACY_LABELS))}",
        )

    raw = await file.read()
    try:
        text = decode_document(file.filename or "document.txt", file.content_type, raw)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    document = models.Document(
        filename=file.filename or "document.txt",
        content_type=file.content_type,
        text=text,
        summary=summarize_text(text),
        privacy_label=privacy_label,
    )
    db.add(document)
    db.flush()

    text_chunks = chunk_text(text)
    chunk_objects: list[models.DocumentChunk] = []
    for index, chunk in enumerate(text_chunks):
        obj = models.DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            text=chunk,
        )
        chunk_objects.append(obj)
        db.add(obj)

    # Generate embeddings before the commit so all writes land in a single
    # transaction and avoid reloading expired objects after the flush.
    for obj in chunk_objects:
        embedding = await ollama.embed(obj.text)
        if embedding is not None:
            obj.embedding = serialize_embedding(embedding)

    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[schemas.DocumentRead])
def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[models.Document]:
    return list(
        db.scalars(
            select(models.Document)
            .order_by(models.Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/{document_id}", response_model=schemas.DocumentDetailRead)
def get_document(document_id: str, db: Session = Depends(get_db)) -> models.Document:
    document = db.get(models.Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_privacy(document, "read_content")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> None:
    document = db.get(models.Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.execute(delete(models.DocumentChunk).where(models.DocumentChunk.document_id == document_id))
    db.delete(document)
    db.commit()


@router.post("/{document_id}/ask", response_model=schemas.DocumentAskRead)
@limiter.limit("20/minute")
async def ask_document(
    request: Request,  # required by slowapi rate limiting
    document_id: str,
    payload: schemas.DocumentAskCreate,
    db: Session = Depends(get_db),
) -> schemas.DocumentAskRead:
    document = db.get(models.Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_privacy(document, "ask")

    chunks = list(
        db.scalars(
            select(models.DocumentChunk)
            .where(models.DocumentChunk.document_id == document_id)
            .order_by(models.DocumentChunk.chunk_index.asc())
        )
    )

    # Try embedding-based semantic search first; fall back to keyword ranking.
    query_embedding = await ollama.embed(payload.question)
    if query_embedding is not None:
        indexed_chunks = [
            (c.chunk_index, c.text, deserialize_embedding(c.embedding)) for c in chunks
        ]
        selected_pairs = semantic_rank_chunks(query_embedding, indexed_chunks)
    else:
        selected_pairs = rank_chunks_with_indices(
            payload.question, [c.text for c in chunks]
        )

    selected_texts = [text for _idx, text in selected_pairs]
    context = "\n\n---\n\n".join(selected_texts)
    prompt = (
        "Answer the question using only the document context. "
        "If the answer is not in the context, say what is missing.\n\n"
        f"Question: {payload.question}\n\nContext:\n{context}"
    )
    answer = await ollama.chat(prompt)
    if not answer:
        answer = (
            "Ollama is not available, so I selected the most relevant document passages instead."
        )

    citations = [
        schemas.ChunkCitation(
            chunk_index=idx,
            document_id=document_id,
            filename=document.filename,
            text=text,
        )
        for idx, text in selected_pairs
    ]

    return schemas.DocumentAskRead(
        answer=answer,
        document_id=document_id,
        context_chunks=selected_texts,
        citations=citations,
    )


