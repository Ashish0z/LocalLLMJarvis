from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=schemas.MemoryRead)
def create_memory(payload: schemas.MemoryCreate, db: Session = Depends(get_db)) -> models.MemoryItem:
    item = models.MemoryItem(
        category=payload.category,
        content=payload.content,
        source=payload.source,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[schemas.MemoryRead])
def list_memory(
    active_only: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[models.MemoryItem]:
    stmt = select(models.MemoryItem).order_by(models.MemoryItem.updated_at.desc()).limit(limit).offset(offset)
    if active_only:
        stmt = stmt.where(models.MemoryItem.is_active.is_(True))
    return list(db.scalars(stmt))


@router.patch("/{memory_id}", response_model=schemas.MemoryRead)
def update_memory(
    memory_id: str, payload: schemas.MemoryUpdate, db: Session = Depends(get_db)
) -> models.MemoryItem:
    item = db.get(models.MemoryItem, memory_id)
    if not item:
        raise HTTPException(status_code=404, detail="Memory item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item

