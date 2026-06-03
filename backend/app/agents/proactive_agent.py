"""
Proactive Agent - Generates proactive messages using OpenAI SDK

This agent initiates conversations based on patterns it observes.
"""
from sqlalchemy.orm import Session
from agents import Agent, ModelSettings, Runner, function_tool

from app.config import ORCHESTRATOR_MODEL, ORCHESTRATOR_TEMPERATURE
from app.observability import trace_agent
from app.tools.context_tools import (
    get_memory_summary_tool,
    get_profile_summary_tool,
    get_recent_history_summary_tool,
)
from app.tools.content_tools import get_content_suggestions_tool


PROACTIVE_AGENT_INSTRUCTIONS = """
You are a proactive wellness coach reaching out to check on the user.

CONTEXT: You are initiating this conversation based on patterns you've observed.

YOUR ROLE:
- Be warm, caring, and non-intrusive
- Acknowledge why you're reaching out
- Offer specific, actionable support
- Keep it brief (2-3 sentences max)
- Include a clear call-to-action or question

TONE:
- Supportive, not pushy
- Personal, not robotic
- Encouraging, not judgmental
- Friendly and conversational

EXAMPLES:

Mental Health Check:
"Hey! I've noticed you've been feeling down the past few days. I'm here if you want to talk about it, or I can suggest some activities that might help. What sounds good?"

Gentle Nudge:
"It's been a few days since we last connected! How are you doing? Want to log how you're feeling today?"

Celebration:
"You've had 5 positive days in a row - that's amazing! 🎉 You're building great momentum. Want to keep the streak going?"

Weekly Support:
"You've logged 45 exercise minutes this week. The weekend is here - want a quick workout suggestion to hit your goal?"

IMPORTANT:
- Use the tools to get context about the user
- Personalize based on their history and preferences
- Suggest specific content when appropriate (use get_content_suggestions tool)
- Always end with a question or clear action
- Keep it conversational and natural
"""


def build_proactive_agent(
    db: Session, 
    user_id: int, 
    intervention_type: str,
    suggested_message: str
) -> Agent:
    """
    Build proactive agent that initiates conversations
    
    Args:
        db: Database session
        user_id: User ID
        intervention_type: Type of intervention (mental_health_check, gentle_nudge, celebrate, weekly_support)
        suggested_message: Suggested message from decision service
    """
    
    @function_tool
    def get_profile_summary() -> dict:
        """Get user profile information"""
        return get_profile_summary_tool(db=db, user_id=user_id)

    @function_tool
    def get_memory_summary(limit: int = 5) -> dict:
        """Get user's stored memories and preferences"""
        return get_memory_summary_tool(db=db, user_id=user_id, limit=limit)

    @function_tool
    def get_recent_history_summary(message_limit: int = 6) -> dict:
        """Get recent conversation history"""
        return get_recent_history_summary_tool(db=db, user_id=user_id, message_limit=message_limit)

    @function_tool
    def get_content_suggestions(
        mood: str | None = None,
        energy_level: str | None = None,
        time_available: int | None = None,
        category: str | None = None,
        limit: int = 2
    ) -> dict:
        """Get personalized content suggestions to include in proactive message"""
        return get_content_suggestions_tool(
            db=db,
            user_id=user_id,
            mood=mood,
            energy_level=energy_level,
            time_available=time_available,
            category=category,
            limit=limit
        )
    
    # Build context-specific instructions
    context_instructions = f"""
INTERVENTION TYPE: {intervention_type}
SUGGESTED MESSAGE: {suggested_message}

Your task:
1. Use the tools to understand the user's context
2. Craft a personalized proactive message based on the intervention type
3. Keep it warm, brief, and actionable
4. End with a clear question or call-to-action
"""
    
    proactive_agent = Agent(
        name="ProactiveWellnessCoach",
        instructions=f"{PROACTIVE_AGENT_INSTRUCTIONS}\n\n{context_instructions}",
        model=ORCHESTRATOR_MODEL,
        model_settings=ModelSettings(
            temperature=ORCHESTRATOR_TEMPERATURE,
            max_tokens=300,  # Keep proactive messages concise
        ),
        tools=[
            get_profile_summary,
            get_memory_summary,
            get_recent_history_summary,
            get_content_suggestions,
        ],
    )
    
    return proactive_agent


@trace_agent("ProactiveWellnessCoach")
async def generate_proactive_message(
    db: Session,
    user_id: int,
    intervention_type: str,
    suggested_message: str
) -> str:
    """
    Generate a proactive message using the agent
    """
    agent = build_proactive_agent(
        db=db,
        user_id=user_id,
        intervention_type=intervention_type,
        suggested_message=suggested_message
    )
    
    # Internal prompt to agent (not shown to user)
    internal_prompt = f"""
Generate a proactive message for this {intervention_type} intervention.

Base it on: {suggested_message}

Steps:
1. Get user context (profile, memory, recent history)
2. Craft a warm, personalized message (2-3 sentences)
3. End with a clear question or action

Remember: You're initiating this conversation, so be friendly and non-intrusive.
"""
    
    result = await Runner.run(agent, input=internal_prompt, max_turns=3)
    return result.final_output
