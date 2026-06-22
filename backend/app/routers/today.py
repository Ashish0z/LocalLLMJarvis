from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/today", tags=["today"])


@router.get("", response_model=schemas.TodayRead)
def get_today(db: Session = Depends(get_db)) -> schemas.TodayRead:
    top_priorities = list(
        db.scalars(
            select(models.Task)
            .where(models.Task.status == "pending")
            .order_by(models.Task.priority_score.desc(), models.Task.created_at.asc())
            .limit(3)
        )
    )
    upcoming_reminders = list(
        db.scalars(
            select(models.Reminder)
            .where(models.Reminder.status == "active")
            .order_by(models.Reminder.remind_at.asc().nullslast(), models.Reminder.created_at.asc())
            .limit(5)
        )
    )
    recent_logs = list(
        db.scalars(select(models.HealthLog).order_by(models.HealthLog.logged_at.desc()).limit(5))
    )

    if top_priorities:
        suggestion = f"Start with: {top_priorities[0].title}"
    elif upcoming_reminders:
        suggestion = f"Next reminder: {upcoming_reminders[0].title}"
    else:
        suggestion = "Capture one important thing for today."

    return schemas.TodayRead(
        generated_at=datetime.now(timezone.utc),
        top_priorities=top_priorities,
        upcoming_reminders=upcoming_reminders,
        recent_logs=recent_logs,
        suggestion=suggestion,
    )

