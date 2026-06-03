"""
Pure Agent Chat Service
All decisions handled by AI agent - no guards, no shortcuts, no pending states
"""
from sqlalchemy.orm import Session

from app.agents.agent_runner import run_main_agent
from app.logging_config import log_flow_step, log_request_start, log_request_end, log_decision
from app.repositories.chat_repository import ChatRepository
from app.services.activity_service import ActivityService
from app.services.context_builder import ContextBuilder
from app.services.memory_service import MemoryService
from app.services.mood_service import MoodService
from app.services.profile_service import ProfileService
from app.services.session_memory_service import SessionMemoryService


class ChatServiceAgentFirst:
    """
    Pure Agent Architecture:
    - AI agent handles ALL decisions
    - No guards, no shortcuts, no pending states
    - Natural, context-aware conversations using conversation history
    """
    
    def __init__(self):
        self.chat_repository = ChatRepository()
        self.context_builder = ContextBuilder()
        self.mood_service = MoodService()
        self.activity_service = ActivityService()
        self.profile_service = ProfileService()
        self.memory_service = MemoryService()
        self.session_memory_service = SessionMemoryService()

    async def process_message(self, db: Session, user_id: int, message: str) -> str:
        """
        Pure Agent Architecture:
        1. Initialize user data
        2. Build context from conversation history
        3. Let AI agent handle EVERYTHING
        
        No guards, no shortcuts, no pending states - just intelligent conversation!
        """
        # Log request start
        log_request_start(user_id, message)
        
        # Initialize user data
        log_flow_step("SETUP", "Initializing user, profile, memories, session")
        self.chat_repository.get_or_create_user(db, user_id)
        self.profile_service.get_or_create_profile(db=db, user_id=user_id)
        self.memory_service.seed_default_memories(db=db, user_id=user_id)
        session = self.chat_repository.get_or_create_active_session(db, user_id)
        log_flow_step("SETUP COMPLETE", f"Session ID: {session.id}")

        # Save user message
        self.chat_repository.save_message(
            db=db,
            session_id=session.id,
            user_id=user_id,
            role='user',
            message=message,
        )

        # Build context with more conversation history for better understanding
        log_flow_step("BUILD_CONTEXT", "Building user context with conversation history")
        self._refresh_session_memory(db=db, session_id=session.id, user_id=user_id)
        user_context = self.context_builder.build_context_packet(
            db=db,
            user_id=user_id,
            session_id=session.id
        )

        # Let the agent handle everything
        log_decision("ROUTE_TO_AGENT", "Routing to agent (pure agent architecture)")
        assistant_reply = await run_main_agent(
            db=db,
            user_id=user_id,
            message=message,
            user_context=user_context,
        )

        self.chat_repository.save_message(
            db=db,
            session_id=session.id,
            user_id=user_id,
            role='assistant',
            message=assistant_reply,
        )

        self._refresh_session_memory(db=db, session_id=session.id, user_id=user_id)
        log_request_end(assistant_reply)
        return assistant_reply

    def _refresh_session_memory(self, db: Session, session_id: int, user_id: int) -> None:
        """Update session memory with recent context"""
        self.session_memory_service.update_session_summary(
            db=db,
            session_id=session_id,
            user_id=user_id,
            recent_messages=self.chat_repository.get_recent_messages(
                db=db,
                user_id=user_id,
                limit=8
            ),
            recent_moods=self.mood_service.get_recent_moods(
                db=db,
                user_id=user_id,
                limit=3
            ),
            recent_activities=self.activity_service.get_recent_activities(
                db=db,
                user_id=user_id,
                limit=5
            ),
        )

    def get_recent_logs(
        self,
        db: Session,
        user_id: int,
        mood_limit: int = 5,
        activity_limit: int = 5
    ) -> dict:
        """Get recent mood and activity logs"""
        moods = self.mood_service.get_recent_moods(
            db=db,
            user_id=user_id,
            limit=mood_limit
        )
        activities = self.activity_service.get_recent_activities(
            db=db,
            user_id=user_id,
            limit=activity_limit
        )

        return {
            'moods': [
                {
                    'mood_label': mood.mood_label,
                    'mood_score': mood.mood_score,
                    'reason': mood.reason,
                    'created_at': mood.created_at.isoformat() if mood.created_at else None,
                }
                for mood in moods
            ],
            'activities': [
                {
                    'activity_category': activity.activity_category,
                    'activity_name': activity.activity_name,
                    'value': activity.value,
                    'unit': activity.unit,
                    'duration_minutes': activity.duration_minutes,
                    'notes': activity.notes,
                    'created_at': activity.created_at.isoformat() if activity.created_at else None,
                }
                for activity in activities
            ],
        }
