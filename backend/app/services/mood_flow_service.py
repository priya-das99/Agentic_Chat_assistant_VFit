"""
Simplified mood flow service for backward compatibility with frontend.
Handles mood draft creation and submission.
"""

from sqlalchemy.orm import Session
from app.models.api_models import MoodDraftResponse
from app.repositories.mood_draft_repository import MoodDraftRepository
from app.services.mood_service import MoodService


class MoodFlowService:
    """Simplified mood flow service - just handles draft CRUD"""
    
    def __init__(self):
        self.draft_repository = MoodDraftRepository()
        self.mood_service = MoodService()
    
    async def start_flow(
        self, 
        db: Session, 
        session_id: int, 
        user_id: int, 
        mood_label: str | None = None, 
        raw_text: str | None = None
    ) -> MoodDraftResponse:
        """Create a mood draft - or auto-log if no reason needed"""
        normalized_mood, mood_score = self.mood_service.normalize_mood(mood_label or "neutral")
        emoji = self.mood_service.get_mood_emoji(normalized_mood)
        needs_reason = self.mood_service.needs_reason_for_mood(normalized_mood)
        
        # Debug logging
        from app.logging_config import logger
        logger.info(f"🎭 Mood Flow Start: {mood_label} → {normalized_mood} (score: {mood_score}, needs_reason: {needs_reason})")
        
        # For positive moods (no reason needed), log immediately and return completed state
        if not needs_reason:
            logger.info(f"✅ Auto-logging positive mood: {normalized_mood}")
            mood_log, challenge_result = self.mood_service.log_mood(
                db=db,
                user_id=user_id,
                mood_label=normalized_mood,
                reason=None,
            )
            
            # Build response message
            message = self.mood_service.build_motivational_reply(mood_log.mood_label, mood_log.reason)
            celebration = challenge_result.get("celebration") if isinstance(challenge_result, dict) else None
            if celebration:
                message = f"{message} {celebration}"
            
            # Return completed response (no draft created)
            return MoodDraftResponse(
                draft_id=0,  # No draft for positive moods
                session_id=session_id,
                user_id=user_id,
                step="completed",
                status="completed",
                prompt=message,
                can_submit=False,  # Already submitted
                draft={
                    "mood_label": mood_log.mood_label,
                    "mood_score": mood_log.mood_score,
                    "emoji": emoji,
                    "reason": None,
                    "reason_label": None,
                },
                log_result={
                    "success": True,
                    "mood_id": mood_log.id,
                    "challenge_result": challenge_result,
                },
                available_options=self.mood_service.get_quick_mood_options(),
                reason_options=[],
            )
        
        # For negative moods, create draft and ask for reason
        logger.info(f"❓ Creating draft for negative mood: {normalized_mood}")
        draft = self.draft_repository.upsert(
            db=db,
            session_id=session_id,
            user_id=user_id,
            step="reason",
            status="pending",
            mood_label=normalized_mood,
            mood_score=mood_score,
            emoji=emoji,
            raw_text=raw_text or mood_label,
            payload={
                "reason": None,
                "reason_label": None,
            },
        )
        
        prompt = self._build_prompt(normalized_mood, needs_reason=True)
        
        return MoodDraftResponse(
            draft_id=draft.id,
            session_id=draft.session_id,
            user_id=draft.user_id,
            step=draft.step,
            status=draft.status,
            prompt=prompt,
            can_submit=False,  # Need reason first
            draft={
                "mood_label": draft.mood_label,
                "mood_score": draft.mood_score,
                "emoji": draft.emoji,
                "reason": None,
                "reason_label": None,
            },
            log_result=None,
            available_options=self.mood_service.get_quick_mood_options(),
            reason_options=self.mood_service.get_reason_options_for_mood(normalized_mood),
        )
    
    async def update_flow(
        self, 
        db: Session, 
        draft_id: int, 
        user_id: int, 
        reason: str | None = None,
        reason_label: str | None = None,
        raw_text: str | None = None,
        **kwargs
    ) -> MoodDraftResponse:
        """Update a mood draft with reason"""
        draft = self.draft_repository.get_by_id(db=db, draft_id=draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        # Update payload
        import json
        payload = json.loads(draft.payload_json) if draft.payload_json else {}
        if reason:
            payload["reason"] = reason
        if reason_label:
            payload["reason_label"] = reason_label
        
        draft = self.draft_repository.update_payload(db=db, draft=draft, payload=payload)
        draft.step = "ready"
        draft.status = "ready"
        db.commit()
        db.refresh(draft)
        
        return MoodDraftResponse(
            draft_id=draft.id,
            session_id=draft.session_id,
            user_id=draft.user_id,
            step=draft.step,
            status=draft.status,
            prompt="Ready to log your mood!",
            can_submit=True,
            draft={
                "mood_label": draft.mood_label,
                "mood_score": draft.mood_score,
                "emoji": draft.emoji,
                "reason": payload.get("reason"),
                "reason_label": payload.get("reason_label"),
            },
            log_result=None,
            available_options=self.mood_service.get_quick_mood_options(),
            reason_options=[],
        )
    
    async def submit_draft(self, db: Session, draft_id: int, user_id: int) -> MoodDraftResponse:
        """Submit the draft and log the mood"""
        draft = self.draft_repository.get_by_id(db=db, draft_id=draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        # Get reason from payload
        import json
        payload = json.loads(draft.payload_json) if draft.payload_json else {}
        reason = payload.get("reason")
        
        # Log the mood
        mood_log, challenge_result = self.mood_service.log_mood(
            db=db,
            user_id=user_id,
            mood_label=draft.mood_label,
            reason=reason,
        )
        
        # Build response message
        message = self.mood_service.build_motivational_reply(mood_log.mood_label, mood_log.reason)
        celebration = challenge_result.get("celebration") if isinstance(challenge_result, dict) else None
        if celebration:
            message = f"{message} {celebration}"
        
        # Clear the draft
        self.draft_repository.clear_by_id(db=db, draft_id=draft_id)
        
        return MoodDraftResponse(
            draft_id=draft.id,
            session_id=draft.session_id,
            user_id=draft.user_id,
            step="completed",
            status="completed",
            prompt=message,
            can_submit=False,
            draft={
                "mood_label": mood_log.mood_label,
                "mood_score": mood_log.mood_score,
                "emoji": self.mood_service.get_mood_emoji(mood_log.mood_label),
                "reason": mood_log.reason,
                "reason_label": payload.get("reason_label"),
            },
            log_result={
                "success": True,
                "mood_id": mood_log.id,
                "challenge_result": challenge_result,
            },
            available_options=self.mood_service.get_quick_mood_options(),
            reason_options=[],
        )
    
    def _build_prompt(self, mood_label: str, needs_reason: bool) -> str:
        """Build prompt for the draft"""
        if needs_reason:
            return f"I've noted you're feeling {mood_label}. Can you share what's making you feel this way?"
        return f"Ready to log your {mood_label} mood!"

