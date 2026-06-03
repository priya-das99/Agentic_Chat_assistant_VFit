from sqlalchemy.orm import Session
from agents import Agent, ModelSettings, Runner, function_tool

from app.agents.instructions import ACTIVITY_AGENT_INSTRUCTIONS
from app.config import ACTIVITY_AGENT_MAX_TOKENS, ACTIVITY_AGENT_MODEL, ACTIVITY_AGENT_TEMPERATURE
from app.logging_config import logger
from app.models.api_models import ActivityDecisionResult
from app.observability import trace_agent
from app.tools.activity_tools import (
    apply_activity_decision_tool,
    get_recent_activities_tool,
    parse_activity_message_tool,
)


def build_activity_agent(db: Session, user_id: int) -> Agent:


    @function_tool
    def get_recent_activities(limit: int = 5) -> dict:
        """
        Get recent activity logs for context.
        Only call this if you need to check what was logged before.
        Do NOT call this for simple logging requests.
        """
        return get_recent_activities_tool(db=db, user_id=user_id, limit=limit)

    @function_tool
    def parse_activity_message(message: str) -> dict:
        """
        STEP 1: Parse user message to extract structured activity data.
        Call this ONCE at the start, then use the result to decide next action.
        Returns a decision contract with actions (log/update/clarify/confirm).
        After calling this, do NOT call it again - use the result you got.
        """
        return parse_activity_message_tool(message)

    @function_tool
    def apply_activity_decision(decision_json: str) -> dict:
        """
        STEP 2: Apply the parsed decision to actually log/update activities.
        Only call this ONCE after parse_activity_message returns log/update actions.
        After this succeeds, STOP and summarize - do not call any more tools.
        Returns: {"applied": [...], "skipped": [...], "message": "..."}
        """
        return apply_activity_decision_tool(db=db, user_id=user_id, decision_json=decision_json)

    return Agent(
        name="ActivityAgent",
        instructions=ACTIVITY_AGENT_INSTRUCTIONS,
        model=ACTIVITY_AGENT_MODEL,
        model_settings=ModelSettings(
            temperature=ACTIVITY_AGENT_TEMPERATURE,
            max_tokens=ACTIVITY_AGENT_MAX_TOKENS,
        ),
        tools=[parse_activity_message, apply_activity_decision, get_recent_activities],
    )


@trace_agent("ActivityAgent")
async def run_activity_agent(db: Session, user_id: int, message: str) -> str:
    try:
        agent = build_activity_agent(db=db, user_id=user_id)
        result = await Runner.run(agent, input=message, max_turns=4)
        return result.final_output
    except Exception as e:
        logger.error(f"❌ Error in ActivityAgent: {e}")
        raise
