from sqlalchemy.orm import Session

from app.agents.agent_runner import run_main_agent
from app.repositories.chat_repository import ChatRepository
from app.services.context_builder import ContextBuilder
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.session_memory_service import SessionMemoryService
from app.services.mood_service import MoodService
from app.services.activity_service import ActivityService
from app.logging_config import logger


class ChatService:
    """
    Simplified chat service - thin orchestration layer.
    
    Responsibilities:
    - Message persistence (save to DB)
    - Context building (gather user data)
    - Agent orchestration (call the orchestrator agent)
    - Session management
    
    The orchestrator agent handles:
    - Intent detection
    - Routing to specialist agents
    - Multi-turn conversations
    - Domain validation
    - Business logic
    """
    
    def __init__(self):
        self.chat_repository = ChatRepository()
        self.context_builder = ContextBuilder()
        self.profile_service = ProfileService()
        self.memory_service = MemoryService()
        self.session_memory_service = SessionMemoryService()
        self.mood_service = MoodService()
        self.activity_service = ActivityService()

    async def process_message(self, db: Session, user_id: int, message: str) -> str:
        """
        Process a user message through the orchestrator agent.
        
        Flow:
        1. Setup user/profile/session
        2. Save user message
        3. Build context
        4. Call orchestrator agent (handles everything!)
        5. Save assistant response
        6. Update session memory
        """
        logger.info(f"\n{'='*80}\n🎯 NEW MESSAGE from User {user_id}: {message}\n{'='*80}")
        
        # 1. Setup
        self.chat_repository.get_or_create_user(db, user_id)
        self.profile_service.get_or_create_profile(db=db, user_id=user_id)
        self.memory_service.seed_default_memories(db=db, user_id=user_id)
        session = self.chat_repository.get_or_create_active_session(db, user_id)

        # 2. Save user message
        self.chat_repository.save_message(
            db=db,
            session_id=session.id,
            user_id=user_id,
            role='user',
            message=message,
        )

        # 3. Build context (profile, recent history, challenges)
        user_context = self.context_builder.build_context_packet(
            db=db, 
            user_id=user_id, 
            session_id=session.id
        )

        # 4. Call orchestrator agent - IT HANDLES EVERYTHING!
        logger.info("🤖 Routing to orchestrator agent")
        assistant_reply = await run_main_agent(
            db=db,
            user_id=user_id,
            message=message,
            user_context=user_context,
        )

        # 5. Save assistant response
        self.chat_repository.save_message(
            db=db,
            session_id=session.id,
            user_id=user_id,
            role='assistant',
            message=assistant_reply,
        )

        # 6. Update session memory
        self._refresh_session_memory(db=db, session_id=session.id, user_id=user_id)
        
        logger.info(f"✅ FINAL RESPONSE: {assistant_reply[:200]}{'...' if len(assistant_reply) > 200 else ''}\n{'='*80}\n")
        return assistant_reply

    def get_recent_logs(self, db: Session, user_id: int, mood_limit: int = 5, activity_limit: int = 5) -> dict:
        """Get recent mood and activity logs for the user."""
        moods = self.mood_service.get_recent_moods(db=db, user_id=user_id, limit=mood_limit)
        activities = self.activity_service.get_recent_activities(db=db, user_id=user_id, limit=activity_limit)

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

    def _refresh_session_memory(self, db: Session, session_id: int, user_id: int) -> None:
        """Update session summary with recent conversation context."""
        self.session_memory_service.update_session_summary(
            db=db,
            session_id=session_id,
            user_id=user_id,
            recent_messages=self.chat_repository.get_recent_messages(db=db, user_id=user_id, limit=8),
            recent_moods=self.mood_service.get_recent_moods(db=db, user_id=user_id, limit=3),
            recent_activities=self.activity_service.get_recent_activities(db=db, user_id=user_id, limit=5),
        )
