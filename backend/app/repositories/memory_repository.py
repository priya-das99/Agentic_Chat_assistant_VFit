from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.db_models import UserMemory


class MemoryRepository:
    def get_recent_memories(self, db: Session, user_id: int, limit: int = 5) -> list[UserMemory]:
        return (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id)
            .order_by(desc(UserMemory.updated_at), desc(UserMemory.created_at))
            .limit(limit)
            .all()
        )

    def find_existing_memory(self, db: Session, user_id: int, fact_text: str) -> UserMemory | None:
        return (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id, UserMemory.fact_text == fact_text)
            .first()
        )

    def create_memory(
        self,
        db: Session,
        user_id: int,
        memory_type: str,
        fact_text: str,
        source: str = "chat",
        confidence: int = 80,
    ) -> UserMemory:
        memory = UserMemory(
            user_id=user_id,
            memory_type=memory_type,
            fact_text=fact_text,
            source=source,
            confidence=confidence,
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def update_memory(self, db: Session, memory: UserMemory, **fields) -> UserMemory:
        for key, value in fields.items():
            setattr(memory, key, value)
        db.commit()
        db.refresh(memory)
        return memory
