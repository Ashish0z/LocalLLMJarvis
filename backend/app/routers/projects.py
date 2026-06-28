from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(project_id: str, db: Session) -> models.Project:
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _milestones_for(project_id: str, db: Session) -> list[models.Milestone]:
    stmt = (
        select(models.Milestone)
        .where(models.Milestone.project_id == project_id)
        .order_by(models.Milestone.sequence_order.asc(), models.Milestone.created_at.asc())
    )
    return list(db.scalars(stmt))


@router.post("", response_model=schemas.ProjectDetailRead, status_code=201)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)) -> dict:
    project = models.Project(
        title=payload.title,
        objective=payload.objective,
        constraints=payload.constraints,
        deadline=payload.deadline,
    )
    db.add(project)
    db.flush()

    milestones = []
    for ms in payload.milestones:
        milestone = models.Milestone(
            project_id=project.id,
            title=ms.title,
            description=ms.description,
            sequence_order=ms.sequence_order,
            due_at=ms.due_at,
        )
        db.add(milestone)
        milestones.append(milestone)

    db.commit()
    db.refresh(project)
    for ms in milestones:
        db.refresh(ms)

    return {**project.__dict__, "milestones": milestones}


@router.get("", response_model=list[schemas.ProjectRead])
def list_projects(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[models.Project]:
    stmt = select(models.Project).order_by(models.Project.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(models.Project.status == status)
    return list(db.scalars(stmt))


@router.get("/{project_id}", response_model=schemas.ProjectDetailRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = _get_project_or_404(project_id, db)
    milestones = _milestones_for(project_id, db)
    return {**project.__dict__, "milestones": milestones}


@router.patch("/{project_id}", response_model=schemas.ProjectDetailRead)
def update_project(
    project_id: str, payload: schemas.ProjectUpdate, db: Session = Depends(get_db)
) -> dict:
    project = _get_project_or_404(project_id, db)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    milestones = _milestones_for(project_id, db)
    return {**project.__dict__, "milestones": milestones}


@router.post("/{project_id}/milestones", response_model=schemas.MilestoneRead, status_code=201)
def add_milestone(
    project_id: str, payload: schemas.MilestoneCreate, db: Session = Depends(get_db)
) -> models.Milestone:
    _get_project_or_404(project_id, db)
    milestone = models.Milestone(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        sequence_order=payload.sequence_order,
        due_at=payload.due_at,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=schemas.MilestoneRead)
def update_milestone(
    project_id: str,
    milestone_id: str,
    payload: schemas.MilestoneUpdate,
    db: Session = Depends(get_db),
) -> models.Milestone:
    _get_project_or_404(project_id, db)
    milestone = db.get(models.Milestone, milestone_id)
    if not milestone or milestone.project_id != project_id:
        raise HTTPException(status_code=404, detail="Milestone not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(milestone, field, value)

    db.commit()
    db.refresh(milestone)
    return milestone


@router.post("/{project_id}/replan", response_model=schemas.ProjectDetailRead)
def replan_project(
    project_id: str, payload: schemas.ProjectReplanCreate, db: Session = Depends(get_db)
) -> dict:
    """Record a slippage reason and optionally replace the milestone plan.

    State behaviour:
    - A *blocked* project is automatically transitioned back to *active*.
    - Projects in any other state (planned, active) remain in their current
      state so replanning can be used proactively without forcing a status change.
    - Passing ``updated_milestones`` as a non-null list replaces all existing
      milestones with the new ones (pass an empty list to clear all milestones).
      Omitting the field (``null``) leaves existing milestones untouched.
    """
    project = _get_project_or_404(project_id, db)

    project.replan_notes = payload.reason
    if project.status == "blocked":
        project.status = "active"

    if payload.updated_milestones is not None:
        existing = _milestones_for(project_id, db)
        for ms in existing:
            db.delete(ms)
        db.flush()

        new_milestones = []
        for ms in payload.updated_milestones:
            milestone = models.Milestone(
                project_id=project_id,
                title=ms.title,
                description=ms.description,
                sequence_order=ms.sequence_order,
                due_at=ms.due_at,
            )
            db.add(milestone)
            new_milestones.append(milestone)
    else:
        new_milestones = _milestones_for(project_id, db)

    db.commit()
    db.refresh(project)
    for ms in new_milestones:
        db.refresh(ms)

    return {**project.__dict__, "milestones": new_milestones}
