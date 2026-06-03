from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.api_models import (
    MoodDraftResponse,
    MoodDraftStartRequest,
    MoodDraftUpdateRequest,
    MoodOptionsResponse,
    MoodQuickActionRequest,
    MoodQuickActionResponse,
)
from app.repositories.chat_repository import ChatRepository
from app.services.mood_flow_service import MoodFlowService
from app.services.mood_service import MoodService

router = APIRouter()
mood_service = MoodService()
mood_flow_service = MoodFlowService()
chat_repository = ChatRepository()


@router.get("/debug/check-logic")
def debug_check_mood_logic(mood_label: str = "neutral"):
    """Debug endpoint to check mood logic"""
    normalized, score = mood_service.normalize_mood(mood_label)
    needs_reason = mood_service.needs_reason_for_mood(mood_label)
    reason_options = mood_service.get_reason_options_for_mood(mood_label)
    
    return {
        "input": mood_label,
        "normalized": normalized,
        "score": score,
        "needs_reason": needs_reason,
        "reason_options_count": len(reason_options),
        "expected_behavior": "ASK for reason" if needs_reason else "AUTO-LOG immediately"
    }


def _resolve_session(db: Session, user_id: int, session_id: int | None) -> int:
    if session_id is not None:
        return session_id
    session = chat_repository.get_or_create_active_session(db=db, user_id=user_id)
    return session.id


@router.get("/quick-options", response_model=MoodOptionsResponse)
def get_quick_mood_options():
    return MoodOptionsResponse(options=mood_service.get_quick_mood_options())


@router.post("/draft/start", response_model=MoodDraftResponse)
async def start_mood_draft(request: MoodDraftStartRequest, db: Session = Depends(get_db)):
    session_id = _resolve_session(db=db, user_id=request.user_id, session_id=request.session_id)
    return await mood_flow_service.start_flow(
        db=db,
        session_id=session_id,
        user_id=request.user_id,
        mood_label=request.mood_label,
        raw_text=request.raw_text,
    )


@router.patch("/draft/{draft_id}", response_model=MoodDraftResponse)
async def update_mood_draft(draft_id: int, request: MoodDraftUpdateRequest, user_id: int = 1, db: Session = Depends(get_db)):
    return await mood_flow_service.update_flow(
        db=db,
        draft_id=draft_id,
        user_id=user_id,
        reason=request.reason,
        reason_label=request.reason_label,
        raw_text=request.raw_text,
    )


@router.post("/draft/{draft_id}/submit", response_model=MoodDraftResponse)
async def submit_mood_draft(draft_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    return await mood_flow_service.submit_draft(db=db, draft_id=draft_id, user_id=user_id)


@router.delete("/draft/{draft_id}")
def cancel_mood_draft(draft_id: int, db: Session = Depends(get_db)):
    mood_flow_service.draft_repository.clear_by_id(db=db, draft_id=draft_id)
    return {"success": True}


@router.post("/quick-log", response_model=MoodQuickActionResponse)
def quick_log_mood(request: MoodQuickActionRequest, db: Session = Depends(get_db)):
    result = mood_service.log_quick_mood(
        db=db,
        user_id=request.user_id,
        mood_label=request.mood_label,
        reason=request.reason,
    )
    return MoodQuickActionResponse(**result)
