"""
Proactive Intervention Service - Orchestrates proactive agent interventions

This service coordinates the decision-making and message generation process.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.agent_decision_service import AgentDecisionService
from app.agents.proactive_agent import generate_proactive_message
from app.repositories.chat_repository import ChatRepository


logger = logging.getLogger(__name__)


class ProactiveInterventionService:
    """
    Service that checks users and sends proactive messages
    
    This is called by the background scheduler to check if users
    need proactive intervention.
    """
    
    def __init__(self):
        self.decision_service = AgentDecisionService()
        self.chat_repo = ChatRepository()
    
    async def run_intervention_check(self, user_id: int):
        """
        Check single user and intervene if needed
        
        Args:
            user_id: User ID to check
        """
        db = SessionLocal()
        
        try:
            # Step 1: Decide if intervention is needed (Python logic - fast & free)
            decision = self.decision_service.should_intervene(db, user_id)
            
            if not decision.should_intervene:
                logger.debug(f"[User {user_id}] No intervention needed: {decision.reason}")
                return
            
            logger.info(f"[User {user_id}] Intervention needed: {decision.intervention_type}")
            logger.info(f"  Reason: {decision.reason}")
            logger.info(f"  Priority: {decision.priority}")
            
            # Step 2: Generate personalized message using agent (OpenAI SDK)
            message = await generate_proactive_message(
                db=db,
                user_id=user_id,
                intervention_type=decision.intervention_type,
                suggested_message=decision.suggested_message
            )
            
            logger.info(f"[User {user_id}] Generated message: {message[:100]}...")
            
            # Step 3: Send message to user
            await self._send_proactive_message(
                db=db,
                user_id=user_id,
                message=message,
                intervention_type=decision.intervention_type,
                priority=decision.priority
            )
            
            logger.info(f"[User {user_id}] Intervention sent successfully")
            
        except Exception as e:
            logger.error(f"[User {user_id}] Error during intervention: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            db.close()
    
    async def _send_proactive_message(
        self,
        db: Session,
        user_id: int,
        message: str,
        intervention_type: str,
        priority: int
    ):
        """
        Send proactive message to user
        
        The message is stored in chat history and will appear when user opens the app.
        In future, this can be extended to send push notifications.
        """
        
        # Store in chat history (will appear in chat when user opens app)
        session = self.chat_repo.get_or_create_active_session(db, user_id)
        
        self.chat_repo.save_message(
            db=db,
            session_id=session.id,
            user_id=user_id,
            role="assistant",
            message=message
        )
        
        # Note: metadata storage would require schema update
        # For now, the message is stored without metadata
        # Future: Add metadata column to ChatMessage table
        
        db.commit()
        
        logger.info(f"[User {user_id}] Proactive message stored in chat history")
        
        # Future: Send push notification
        # await self._send_push_notification(user_id, message)
        
        # Future: Send email notification
        # await self._send_email_notification(user_id, message)
