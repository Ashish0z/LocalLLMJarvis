from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("", response_model=schemas.HealthLogRead)
def create_log(payload: schemas.HealthLogCreate, db: Session = Depends(get_db)) -> models.HealthLog:
    log = models.HealthLog(
        kind=payload.kind,
        value=payload.value,
        amount=payload.amount,
        unit=payload.unit,
        logged_at=payload.logged_at or datetime.now(timezone.utc),
        source=payload.source,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/water", response_model=schemas.HealthLogRead)
def create_water_log(payload: schemas.WaterLogCreate, db: Session = Depends(get_db)) -> models.HealthLog:
    log = models.HealthLog(
        kind="water",
        value=payload.value,
        amount=payload.amount,
        unit=payload.unit,
        logged_at=payload.logged_at or datetime.now(timezone.utc),
        source=payload.source,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/nutrition", response_model=schemas.HealthLogRead)
def create_nutrition_log(
    payload: schemas.NutritionLogCreate, db: Session = Depends(get_db)
) -> models.HealthLog:
    log = models.HealthLog(
        kind="nutrition",
        value=payload.value,
        logged_at=payload.logged_at or datetime.now(timezone.utc),
        source=payload.source,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[schemas.HealthLogRead])
def list_logs(
    kind: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[models.HealthLog]:
    stmt = select(models.HealthLog).order_by(models.HealthLog.logged_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(models.HealthLog.kind == kind)
    return list(db.scalars(stmt))
