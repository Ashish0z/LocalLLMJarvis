from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.prioritization import score_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=schemas.TaskRead)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)) -> models.Task:
    priority_score, priority_reason = score_task(payload.title, payload.due_at)
    task = models.Task(
        title=payload.title,
        notes=payload.notes,
        due_at=payload.due_at,
        priority_score=priority_score,
        priority_reason=priority_reason,
        source=payload.source,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[schemas.TaskRead])
def list_tasks(
    status: str | None = Query(default="pending"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[models.Task]:
    stmt = select(models.Task).order_by(models.Task.priority_score.desc(), models.Task.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(models.Task.status == status)
    return list(db.scalars(stmt))


@router.patch("/{task_id}", response_model=schemas.TaskRead)
def update_task(
    task_id: str, payload: schemas.TaskUpdate, db: Session = Depends(get_db)
) -> models.Task:
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(task, field, value)

    if "title" in data or "due_at" in data:
        task.priority_score, task.priority_reason = score_task(task.title, task.due_at)

    db.commit()
    db.refresh(task)
    return task

