from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.db_models import ChatSession, ChatMessage, User
from datetime import datetime


class ChatRepository:
    def get_or_create_user(self, db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, name="Demo User")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def get_or_create_active_session(self, db: Session, user_id: int) -> ChatSession:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id, ChatSession.status == "active")
            .order_by(desc(ChatSession.started_at))
            .first()
        )

        if not session:
            session = ChatSession(user_id=user_id, status="active")
            db.add(session)
            db.commit()
            db.refresh(session)

        return session

    def save_message(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        role: str,
        message: str,
    ) -> ChatMessage:
        chat_message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=message,
        )
        db.add(chat_message)

        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.last_message_at = datetime.utcnow()

        db.commit()
        db.refresh(chat_message)
        return chat_message

    def get_recent_messages(self, db: Session, user_id: int, limit: int = 10) -> list[ChatMessage]:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .all()
        )
