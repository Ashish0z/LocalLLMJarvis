from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.limiter import limiter
from app.services.assistant import AssistantService

router = APIRouter(prefix="/assistant", tags=["assistant"])
assistant_service = AssistantService()


@router.post("/message", response_model=schemas.AssistantMessageRead)
@limiter.limit("30/minute")
async def create_assistant_message(
    request: Request,
    payload: schemas.AssistantMessageCreate,
    db: Session = Depends(get_db),
) -> dict:
    return await assistant_service.handle_message(db, payload.text, payload.source)

