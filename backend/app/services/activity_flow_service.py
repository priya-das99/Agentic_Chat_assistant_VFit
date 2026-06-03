"""
DEPRECATED: Activity flow service is no longer used.
The orchestrator agent now handles multi-turn conversations naturally.

This stub exists only for backward compatibility with API endpoints.
Consider removing the /activity/draft/* endpoints from the API.
"""

from sqlalchemy.orm import Session
from app.models.api_models import ActivityDraftResponse
from app.repositories.activity_draft_repository import ActivityDraftRepository


class ActivityFlowService:
    """Deprecated stub - agent handles flows now"""
    
    def __init__(self):
        self.draft_repository = ActivityDraftRepository()
    
    def start_flow(self, db: Session, session_id: int, user_id: int, activity_name: str, duration_minutes: int | None = None, raw_text: str | None = None) -> ActivityDraftResponse:
        raise NotImplementedError("Activity flows are handled by the agent now. Use /chat endpoint instead.")
    
    def update_flow(self, db: Session, draft_id: int, user_id: int, **kwargs) -> ActivityDraftResponse:
        raise NotImplementedError("Activity flows are handled by the agent now. Use /chat endpoint instead.")
    
    def submit_draft(self, db: Session, draft_id: int, user_id: int) -> ActivityDraftResponse:
        raise NotImplementedError("Activity flows are handled by the agent now. Use /chat endpoint instead.")
