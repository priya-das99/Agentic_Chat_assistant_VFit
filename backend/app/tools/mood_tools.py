from sqlalchemy.orm import Session

from app.models.api_models import MoodLogInput
from app.services.mood_service import MoodService

mood_service = MoodService()


def log_mood_tool(db: Session, user_id: int, mood_label: str, reason: str | None = None) -> dict:
    mood_input = MoodLogInput(mood_label=mood_label, reason=reason)
    mood_log, challenge_result = mood_service.log_mood(
        db=db,
        user_id=user_id,
        mood_label=mood_input.mood_label,
        reason=mood_input.reason,
    )

    return {
        "success": True,
        "mood_id": mood_log.id,
        "mood_label": mood_log.mood_label,
        "mood_score": mood_log.mood_score,
        "reason": mood_log.reason,
        "message": "Mood logged successfully",
        "challenge_result": challenge_result,
    }


def get_recent_moods_tool(db: Session, user_id: int, limit: int = 5) -> dict:
    moods = mood_service.get_recent_moods(db=db, user_id=user_id, limit=limit)
    return {
        "items": [
            {
                "mood_label": mood.mood_label,
                "mood_score": mood.mood_score,
                "reason": mood.reason,
                "created_at": mood.created_at.isoformat() if mood.created_at else None,
            }
            for mood in moods
        ]
    }


def parse_mood_message_tool(message: str) -> dict:
    return mood_service.parse_mood_text(message).model_dump()
