from sqlalchemy.orm import Session
from agents import Agent, ModelSettings, Runner, function_tool

from app.agents.instructions import CHALLENGE_AGENT_INSTRUCTIONS
from app.config import CHALLENGE_AGENT_MAX_TOKENS, CHALLENGE_AGENT_MODEL, CHALLENGE_AGENT_TEMPERATURE
from app.logging_config import logger
from app.observability import trace_agent
from app.tools.challenge_tools import (
    get_challenge_coach_snapshot_tool,
    get_challenge_reminders_tool,
    get_challenge_summary_tool,
    get_current_challenges_tool,
    record_challenge_progress_tool,
    record_step_progress_tool,
)


def build_challenge_agent(db: Session, user_id: int) -> Agent:
    @function_tool
    def get_current_challenges() -> dict:
        return get_current_challenges_tool(db=db, user_id=user_id)

    @function_tool
    def get_challenge_summary() -> dict:
        return get_challenge_summary_tool(db=db, user_id=user_id)

    @function_tool
    def get_challenge_reminders() -> dict:
        return get_challenge_reminders_tool(db=db, user_id=user_id)

    @function_tool
    def get_challenge_coach_snapshot(message: str) -> dict:
        return get_challenge_coach_snapshot_tool(db=db, user_id=user_id, message=message)

    @function_tool
    def record_challenge_progress(
        challenge_code: str | None = None,
        metric_key: str | None = None,
        value: int | None = None,
        message: str | None = None,
    ) -> dict:
        return record_challenge_progress_tool(
            db=db,
            user_id=user_id,
            challenge_code=challenge_code,
            metric_key=metric_key,
            value=value,
            message=message,
        )

    @function_tool
    def record_step_progress(steps: int, message: str | None = None) -> dict:
        return record_step_progress_tool(db=db, user_id=user_id, steps=steps, message=message)

    return Agent(
        name="ChallengeAgent",
        instructions=CHALLENGE_AGENT_INSTRUCTIONS,
        model=CHALLENGE_AGENT_MODEL,
        model_settings=ModelSettings(
            temperature=CHALLENGE_AGENT_TEMPERATURE,
            max_tokens=CHALLENGE_AGENT_MAX_TOKENS,
        ),
        tools=[
            get_challenge_coach_snapshot,
            get_current_challenges,
            get_challenge_summary,
            get_challenge_reminders,
            record_challenge_progress,
            record_step_progress,
        ],
    )


@trace_agent("ChallengeAgent")
async def run_challenge_agent(db: Session, user_id: int, message: str) -> str:
    try:
        agent = build_challenge_agent(db=db, user_id=user_id)
        result = await Runner.run(agent, input=message, max_turns=8)
        return result.final_output
    except Exception as e:
        logger.error(f"❌ Error in ChallengeAgent: {e}")
        raise
