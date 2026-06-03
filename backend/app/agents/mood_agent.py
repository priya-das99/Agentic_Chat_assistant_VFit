from sqlalchemy.orm import Session
from agents import Agent, ModelSettings, Runner, function_tool

from app.agents.instructions import MOOD_AGENT_INSTRUCTIONS
from app.config import MOOD_AGENT_MAX_TOKENS, MOOD_AGENT_MODEL, MOOD_AGENT_TEMPERATURE
from app.logging_config import logger
from app.observability import trace_agent
from app.tools.mood_tools import get_recent_moods_tool, log_mood_tool, parse_mood_message_tool


def build_mood_agent(db: Session, user_id: int) -> Agent:
    @function_tool
    def log_mood(mood_label: str, reason: str | None = None) -> dict:
        return log_mood_tool(
            db=db,
            user_id=user_id,
            mood_label=mood_label,
            reason=reason,
        )

    @function_tool
    def get_recent_moods(limit: int = 5) -> dict:
        return get_recent_moods_tool(db=db, user_id=user_id, limit=limit)

    @function_tool
    def parse_mood_message(message: str) -> dict:
        return parse_mood_message_tool(message)

    return Agent(
        name="MoodAgent",
        instructions=MOOD_AGENT_INSTRUCTIONS,
        model=MOOD_AGENT_MODEL,
        model_settings=ModelSettings(
            temperature=MOOD_AGENT_TEMPERATURE,
            max_tokens=MOOD_AGENT_MAX_TOKENS,
        ),
        tools=[parse_mood_message, log_mood, get_recent_moods],
    )


@trace_agent("MoodAgent")
async def run_mood_agent(db: Session, user_id: int, message: str) -> str:
    try:
        agent = build_mood_agent(db=db, user_id=user_id)
        result = await Runner.run(agent, input=message, max_turns=8)
        return result.final_output
    except Exception as e:
        logger.error(f"❌ Error in MoodAgent: {e}")
        raise
