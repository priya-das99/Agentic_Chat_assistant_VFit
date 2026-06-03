from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.api_models import ChatMessageRequest, ChatMessageResponse, RecentLogsResponse
from app.services.chat_service_agent_first import ChatServiceAgentFirst

router = APIRouter()
chat_service = ChatServiceAgentFirst()


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest, db: Session = Depends(get_db)):
    reply = await chat_service.process_message(
        db=db,
        user_id=request.user_id,
        message=request.message,
    )
    return ChatMessageResponse(reply=reply)


@router.get("/logs", response_model=RecentLogsResponse)
def get_recent_logs(user_id: int = 1, db: Session = Depends(get_db)):
    logs = chat_service.get_recent_logs(db=db, user_id=user_id)
    return RecentLogsResponse(**logs)
