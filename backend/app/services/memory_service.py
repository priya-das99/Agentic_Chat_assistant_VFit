from app.repositories.memory_repository import MemoryRepository


class MemoryService:
    DEFAULT_MEMORIES = [
        ("preference", "User prefers badminton over gym workouts", "seed", 95),
        ("pattern", "Poor sleep often leads to stress the next day", "seed", 90),
        ("goal", "User wants consistency more than intensity", "seed", 90),
    ]

    def __init__(self):
        self.memory_repository = MemoryRepository()

    def seed_default_memories(self, db, user_id: int) -> None:
        existing = self.memory_repository.get_recent_memories(db=db, user_id=user_id, limit=1)
        if existing:
            return

        for memory_type, fact_text, source, confidence in self.DEFAULT_MEMORIES:
            self.memory_repository.create_memory(
                db=db,
                user_id=user_id,
                memory_type=memory_type,
                fact_text=fact_text,
                source=source,
                confidence=confidence,
            )

    def get_recent_memories(self, db, user_id: int, limit: int = 5):
        self.seed_default_memories(db=db, user_id=user_id)
        return self.memory_repository.get_recent_memories(db=db, user_id=user_id, limit=limit)

    def store_memory_fact(
        self,
        db,
        user_id: int,
        memory_type: str,
        fact_text: str,
        source: str = "chat",
        confidence: int = 80,
    ):
        existing = self.memory_repository.find_existing_memory(db=db, user_id=user_id, fact_text=fact_text)
        if existing:
            return self.memory_repository.update_memory(
                db=db,
                memory=existing,
                memory_type=memory_type,
                source=source,
                confidence=confidence,
            )

        return self.memory_repository.create_memory(
            db=db,
            user_id=user_id,
            memory_type=memory_type,
            fact_text=fact_text,
            source=source,
            confidence=confidence,
        )

    def format_memory_summary(self, memories) -> str:
        if not memories:
            return "No durable memory facts yet."

        return "\n".join(
            f"- [{memory.memory_type}] {memory.fact_text}"
            for memory in memories
        )
