from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.limiter import limiter
from app.services.documents import chunk_text, decode_document, rank_chunks, summarize_text
from app.services.ollama import OllamaClient

router = APIRouter(prefix="/documents", tags=["documents"])
ollama = OllamaClient()


@router.post("", response_model=schemas.DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> models.Document:
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
    )
    db.add(document)
    db.flush()

    for index, chunk in enumerate(chunk_text(text)):
        db.add(models.DocumentChunk(document_id=document.id, chunk_index=index, text=chunk))

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
    request: Request,
    document_id: str,
    payload: schemas.DocumentAskCreate,
    db: Session = Depends(get_db),
) -> schemas.DocumentAskRead:
    document = db.get(models.Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = list(
        db.scalars(
            select(models.DocumentChunk)
            .where(models.DocumentChunk.document_id == document_id)
            .order_by(models.DocumentChunk.chunk_index.asc())
        )
    )
    selected = rank_chunks(payload.question, [chunk.text for chunk in chunks])
    context = "\n\n---\n\n".join(selected)
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

    return schemas.DocumentAskRead(
        answer=answer,
        document_id=document_id,
        context_chunks=selected,
    )

