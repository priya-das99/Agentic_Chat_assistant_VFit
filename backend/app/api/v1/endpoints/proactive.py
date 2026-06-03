"""
Proactive intervention endpoints for testing and monitoring
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.agent_decision_service import AgentDecisionService
from app.services.proactive_intervention_service import ProactiveInterventionService

router = APIRouter()
decision_service = AgentDecisionService()
intervention_service = ProactiveInterventionService()


@router.get("/check-decision/{user_id}")
async def check_intervention_decision(user_id: int, db: Session = Depends(get_db)):
    """
    Test endpoint: Check if user needs intervention
    
    Returns the decision without actually sending the intervention.
    Useful for testing the decision logic.
    """
    decision = decision_service.should_intervene(db=db, user_id=user_id, check_last_intervention=False)
    
    return {
        "user_id": user_id,
        "should_intervene": decision.should_intervene,
        "intervention_type": decision.intervention_type,
        "reason": decision.reason,
        "priority": decision.priority,
        "suggested_message": decision.suggested_message,
        "timing": decision.timing
    }


@router.post("/trigger-intervention/{user_id}")
async def trigger_intervention(user_id: int):
    """
    Test endpoint: Manually trigger intervention for user
    
    This will check if intervention is needed and send it if appropriate.
    Useful for testing the full intervention flow.
    """
    await intervention_service.run_intervention_check(user_id)
    
    return {
        "message": f"Intervention check triggered for user {user_id}",
        "status": "completed",
        "note": "Check chat history to see if proactive message was sent"
    }
