from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("", response_model=schemas.ReminderRead)
def create_reminder(payload: schemas.ReminderCreate, db: Session = Depends(get_db)) -> models.Reminder:
    reminder = models.Reminder(
        title=payload.title,
        remind_at=payload.remind_at,
        intensity=payload.intensity,
        recurrence=payload.recurrence,
        source=payload.source,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("", response_model=list[schemas.ReminderRead])
def list_reminders(
    status: str | None = Query(default="active"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[models.Reminder]:
    stmt = select(models.Reminder).order_by(models.Reminder.remind_at.asc().nullslast(), models.Reminder.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(models.Reminder.status == status)
    return list(db.scalars(stmt))


@router.patch("/{reminder_id}", response_model=schemas.ReminderRead)
def update_reminder(
    reminder_id: str, payload: schemas.ReminderUpdate, db: Session = Depends(get_db)
) -> models.Reminder:
    reminder = db.get(models.Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)

    db.commit()
    db.refresh(reminder)
    return reminder

