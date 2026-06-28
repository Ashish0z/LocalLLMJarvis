from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/habits", tags=["habits"])


def _apply_checkin_to_streak(habit: models.Habit, outcome: str) -> None:
    if outcome == "complete":
        habit.current_streak += 1
        if habit.current_streak > habit.longest_streak:
            habit.longest_streak = habit.current_streak
    elif outcome == "relapse":
        habit.relapse_count += 1
        habit.current_streak = 0
    # "skip" leaves current_streak unchanged – neither advancing nor resetting it


@router.post("", response_model=schemas.HabitRead, status_code=201)
def create_habit(payload: schemas.HabitCreate, db: Session = Depends(get_db)) -> models.Habit:
    habit = models.Habit(
        title=payload.title,
        mode=payload.mode,
        description=payload.description,
        cue=payload.cue,
        frequency=payload.frequency,
        coaching_tone=payload.coaching_tone,
        source=payload.source,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


@router.get("", response_model=list[schemas.HabitRead])
def list_habits(
    status: str | None = Query(default="active"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[models.Habit]:
    stmt = select(models.Habit).order_by(models.Habit.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(models.Habit.status == status)
    return list(db.scalars(stmt))


@router.patch("/{habit_id}", response_model=schemas.HabitRead)
def update_habit(
    habit_id: str, payload: schemas.HabitUpdate, db: Session = Depends(get_db)
) -> models.Habit:
    habit = db.get(models.Habit, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)

    db.commit()
    db.refresh(habit)
    return habit


@router.post("/{habit_id}/checkins", response_model=schemas.HabitCheckInRead, status_code=201)
def create_habit_checkin(
    habit_id: str, payload: schemas.HabitCheckInCreate, db: Session = Depends(get_db)
) -> models.HabitCheckIn:
    habit = db.get(models.Habit, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    checked_at = payload.checked_at or datetime.now(timezone.utc)
    checkin = models.HabitCheckIn(
        habit_id=habit_id,
        outcome=payload.outcome,
        notes=payload.notes,
        checked_at=checked_at,
    )
    db.add(checkin)

    _apply_checkin_to_streak(habit, payload.outcome)

    db.commit()
    db.refresh(checkin)
    return checkin


@router.get("/{habit_id}/checkins", response_model=list[schemas.HabitCheckInRead])
def list_habit_checkins(
    habit_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[models.HabitCheckIn]:
    habit = db.get(models.Habit, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    stmt = (
        select(models.HabitCheckIn)
        .where(models.HabitCheckIn.habit_id == habit_id)
        .order_by(models.HabitCheckIn.checked_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
