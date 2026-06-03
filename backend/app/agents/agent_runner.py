from sqlalchemy.orm import Session

from app.agents.fitness_agent import run_fitness_agent


async def run_main_agent(db: Session, user_id: int, message: str, user_context: str) -> str:
    return await run_fitness_agent(
        db=db,
        user_id=user_id,
        message=message,
        user_context=user_context,
    )
