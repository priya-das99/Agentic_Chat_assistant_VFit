from sqlalchemy.orm import Session
from agents import Agent, ModelSettings, Runner, function_tool

from app.agents.activity_agent import build_activity_agent
from app.agents.challenge_agent import build_challenge_agent
from app.agents.instructions import ORCHESTRATOR_AGENT_INSTRUCTIONS
from app.agents.mood_agent import build_mood_agent
from app.config import ORCHESTRATOR_MAX_TOKENS, ORCHESTRATOR_MODEL, ORCHESTRATOR_TEMPERATURE
from app.logging_config import logger
from app.observability import trace_agent
from app.tools.context_tools import (
    get_challenge_summary_tool,
    get_memory_summary_tool,
    get_profile_summary_tool,
    get_recent_history_summary_tool,
)
from app.tools.content_tools import get_content_suggestions_tool


def build_fitness_agent(db: Session, user_id: int, user_context: str) -> Agent:
    mood_agent = build_mood_agent(db=db, user_id=user_id)
    activity_agent = build_activity_agent(db=db, user_id=user_id)
    challenge_agent = build_challenge_agent(db=db, user_id=user_id)

    @function_tool
    def get_profile_summary() -> dict:
        return get_profile_summary_tool(db=db, user_id=user_id)

    @function_tool
    def get_memory_summary(limit: int = 5) -> dict:
        return get_memory_summary_tool(db=db, user_id=user_id, limit=limit)

    @function_tool
    def get_recent_history_summary(message_limit: int = 6) -> dict:
        return get_recent_history_summary_tool(db=db, user_id=user_id, message_limit=message_limit)

    @function_tool
    def get_challenge_summary() -> dict:
        return get_challenge_summary_tool(db=db, user_id=user_id)

    @function_tool
    def get_content_suggestions(
        mood: str | None = None,
        energy_level: str | None = None,
        time_available: int | None = None,
        time_of_day: str | None = None,
        category: str | None = None,
        content_type: str | None = None,
        limit: int = 3
    ) -> dict:
        """Get personalized content suggestions (videos, articles, music, guides) based on user's current state"""
        result = get_content_suggestions_tool(
            db=db,
            user_id=user_id,
            mood=mood,
            energy_level=energy_level,
            time_available=time_available,
            time_of_day=time_of_day,
            category=category,
            content_type=content_type,
            limit=limit
        )
        return result

    orchestrator_agent = Agent(
        name="FitnessCoachOrchestrator",
        instructions=f"{ORCHESTRATOR_AGENT_INSTRUCTIONS}\n\nCurrent user context:\n{user_context}\n\nIMPORTANT: When you have enough information to respond, produce a final answer WITHOUT calling more tools. If a tool gives you a complete answer, use it and STOP.",
        model=ORCHESTRATOR_MODEL,
        model_settings=ModelSettings(
            temperature=ORCHESTRATOR_TEMPERATURE,
            max_tokens=ORCHESTRATOR_MAX_TOKENS,
        ),
        tools=[
            get_profile_summary,
            get_memory_summary,
            get_recent_history_summary,
            get_content_suggestions,
            mood_agent.as_tool(
                tool_name="use_mood_agent",
                tool_description="Handle mood-related conversations and logging. Call ONCE then use the result. Do not call again if you already got an answer.",
            ),
            activity_agent.as_tool(
                tool_name="use_activity_agent",
                tool_description="Handle water, sleep, exercise, sports logging. Call ONCE then use the result. Do not call again if you already got an answer.",
            ),
            challenge_agent.as_tool(
                tool_name="use_challenge_agent",
                tool_description="Handle challenges, points, progress. Call ONCE then use the result. Do not call again if you already got an answer.",
            ),
            get_challenge_summary,
        ],
    )

    return orchestrator_agent


@trace_agent("FitnessCoachOrchestrator")
async def run_fitness_agent(db: Session, user_id: int, message: str, user_context: str) -> str:
    try:
        agent = build_fitness_agent(db=db, user_id=user_id, user_context=user_context)
        result = await Runner.run(agent, input=message, max_turns=5)
        return result.final_output
    except Exception as e:
        logger.error(f"❌ Error in FitnessCoachOrchestrator: {e}")
        raise
