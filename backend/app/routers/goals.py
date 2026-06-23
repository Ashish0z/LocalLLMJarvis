import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=schemas.GoalRead, status_code=201)
def create_goal(payload: schemas.GoalCreate, db: Session = Depends(get_db)) -> models.Goal:
    goal = models.Goal(
        title=payload.title,
        description=payload.description,
        target_date=payload.target_date,
        source=payload.source,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("", response_model=list[schemas.GoalRead])
def list_goals(
    status: str | None = Query(default="active"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[models.Goal]:
    stmt = select(models.Goal).order_by(models.Goal.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(models.Goal.status == status)
    return list(db.scalars(stmt))


@router.patch("/{goal_id}", response_model=schemas.GoalRead)
def update_goal(
    goal_id: str, payload: schemas.GoalUpdate, db: Session = Depends(get_db)
) -> models.Goal:
    goal = db.get(models.Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)

    db.commit()
    db.refresh(goal)
    return goal


@router.post("/{goal_id}/interview", response_model=schemas.GoalRead)
def submit_goal_interview(
    goal_id: str, payload: schemas.GoalInterviewCreate, db: Session = Depends(get_db)
) -> models.Goal:
    goal = db.get(models.Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.baseline_data = json.dumps(payload.model_dump(exclude_none=True))

    db.commit()
    db.refresh(goal)
    return goal


@router.post("/{goal_id}/checkins", response_model=schemas.GoalCheckInRead, status_code=201)
def create_goal_checkin(
    goal_id: str, payload: schemas.GoalCheckInCreate, db: Session = Depends(get_db)
) -> models.GoalCheckIn:
    goal = db.get(models.Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    checkin = models.GoalCheckIn(
        goal_id=goal_id,
        notes=payload.notes,
        adherence_rating=payload.adherence_rating,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


@router.get("/{goal_id}/checkins", response_model=list[schemas.GoalCheckInRead])
def list_goal_checkins(
    goal_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[models.GoalCheckIn]:
    goal = db.get(models.Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    stmt = (
        select(models.GoalCheckIn)
        .where(models.GoalCheckIn.goal_id == goal_id)
        .order_by(models.GoalCheckIn.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
