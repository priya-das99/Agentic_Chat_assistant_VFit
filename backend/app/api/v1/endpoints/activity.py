from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.api_models import (
    ActivityCatalogResponse,
    ActivityDraftResponse,
    ActivityDraftStartRequest,
    ActivityDraftUpdateRequest,
)
from app.repositories.chat_repository import ChatRepository
from app.services.activity_flow_service import ActivityFlowService

router = APIRouter()
activity_flow_service = ActivityFlowService()
chat_repository = ChatRepository()


def _resolve_session(db: Session, user_id: int, session_id: int | None) -> int:
    if session_id is not None:
        return session_id
    session = chat_repository.get_or_create_active_session(db=db, user_id=user_id)
    return session.id


@router.get("/catalog", response_model=ActivityCatalogResponse)
def get_activity_catalog(db: Session = Depends(get_db)):
    categories = activity_flow_service.get_catalog(db=db)
    return ActivityCatalogResponse(categories=categories)


@router.post("/draft/start", response_model=ActivityDraftResponse)
def start_activity_draft(request: ActivityDraftStartRequest, db: Session = Depends(get_db)):
    session_id = _resolve_session(db=db, user_id=request.user_id, session_id=request.session_id)
    return activity_flow_service.start_flow(
        db=db,
        session_id=session_id,
        user_id=request.user_id,
        category_key=request.category_key,
        activity_key=request.activity_key,
    )


@router.patch("/draft/{draft_id}", response_model=ActivityDraftResponse)
def update_activity_draft(draft_id: int, request: ActivityDraftUpdateRequest, user_id: int = 1, db: Session = Depends(get_db)):
    session_id = None
    return activity_flow_service.update_flow(
        db=db,
        draft_id=draft_id,
        session_id=session_id,
        user_id=user_id,
        category_key=request.category_key,
        activity_key=request.activity_key,
        activity_date=request.activity_date,
        activity_time=request.activity_time,
        duration_minutes=request.duration_minutes,
        raw_text=request.raw_text,
    )


@router.post("/draft/{draft_id}/submit", response_model=ActivityDraftResponse)
def submit_activity_draft(draft_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    return activity_flow_service.submit_draft(db=db, draft_id=draft_id, user_id=user_id)


@router.delete("/draft/{draft_id}")
def cancel_activity_draft(draft_id: int, db: Session = Depends(get_db)):
    activity_flow_service.draft_repository.clear_by_id(db=db, draft_id=draft_id)
    return {"success": True}
