"""
Content recommendation tools for agent
"""

from sqlalchemy.orm import Session
from app.services.recommendation_service import RecommendationService

recommendation_service = RecommendationService()


def get_content_suggestions_tool(
    db: Session,
    user_id: int,
    mood: str | None = None,
    energy_level: str | None = None,
    time_available: int | None = None,
    time_of_day: str | None = None,
    category: str | None = None,
    content_type: str | None = None,
    limit: int = 3
) -> dict:
    """
    Get personalized content suggestions (videos, articles, music, guides).
    
    Use this when user:
    - Asks for suggestions or recommendations
    - Needs help with stress, anxiety, sleep, motivation
    - Wants something to do or watch
    - Asks "what should I do?"
    
    Parameters:
    - mood: User's current mood (stressed, anxious, tired, happy, sad, energetic, etc.)
    - energy_level: User's energy level (low, medium, high)
    - time_available: Minutes user has available
    - time_of_day: Current time (morning, afternoon, evening, anytime)
    - category: Specific category (meditation, yoga, cardio, stress_relief, sleep_aid, etc.)
    - content_type: Type of content (video, article, audio, guide)
    - limit: Number of suggestions (default 3)
    
    Returns:
    - suggestions: List of content items with title, url, description, reason
    - count: Number of suggestions found
    
    Example usage:
    - User says "I'm stressed" → get_content_suggestions(mood="stressed")
    - User says "I can't sleep" → get_content_suggestions(mood="anxious", category="sleep_aid", time_of_day="evening")
    - User says "I have 10 minutes" → get_content_suggestions(time_available=10)
    """
    context = {}
    
    if mood:
        context["mood"] = mood
    if energy_level:
        context["energy_level"] = energy_level
    if time_available:
        context["time_available"] = time_available
    if time_of_day:
        context["time_of_day"] = time_of_day
    if category:
        context["category"] = category
    if content_type:
        context["content_type"] = content_type
    
    suggestions = recommendation_service.get_personalized_content(
        db=db,
        user_id=user_id,
        context=context,
        limit=limit
    )
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "message": f"Found {len(suggestions)} personalized suggestions" if suggestions else "No suggestions found. Try different criteria."
    }
