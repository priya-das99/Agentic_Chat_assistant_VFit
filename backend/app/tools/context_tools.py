from app.repositories.chat_repository import ChatRepository
from app.services.challenge_service import ChallengeService
from app.services.activity_service import ActivityService
from app.services.memory_service import MemoryService
from app.services.mood_service import MoodService
from app.services.profile_service import ProfileService

chat_repository = ChatRepository()
profile_service = ProfileService()
memory_service = MemoryService()
mood_service = MoodService()
activity_service = ActivityService()
challenge_service = ChallengeService()


def get_profile_summary_tool(db, user_id: int) -> dict:
    profile = profile_service.get_or_create_profile(db=db, user_id=user_id)
    return {
        "summary": profile_service.format_profile_summary(profile),
        "fitness_goal": profile.fitness_goal,
        "activity_level": profile.activity_level,
        "preferred_activities": profile.preferred_activities,
        "limitations": profile.limitations,
    }


def get_memory_summary_tool(db, user_id: int, limit: int = 5) -> dict:
    memories = memory_service.get_recent_memories(db=db, user_id=user_id, limit=limit)
    return {
        "summary": memory_service.format_memory_summary(memories),
        "items": [
            {
                "memory_type": memory.memory_type,
                "fact_text": memory.fact_text,
                "source": memory.source,
                "confidence": memory.confidence,
            }
            for memory in memories
        ],
    }


def get_recent_history_summary_tool(db, user_id: int, message_limit: int = 6) -> dict:
    recent_messages = chat_repository.get_recent_messages(db=db, user_id=user_id, limit=message_limit)
    recent_moods = mood_service.get_recent_moods(db=db, user_id=user_id, limit=3)
    recent_activities = activity_service.get_recent_activities(db=db, user_id=user_id, limit=5)
    challenge_summary = challenge_service.get_summary(db=db, user_id=user_id)

    message_lines = [f"{message.role}: {message.message}" for message in reversed(recent_messages)]
    mood_lines = [
        {
            "mood_label": mood.mood_label,
            "reason": mood.reason,
            "created_at": mood.created_at.isoformat() if mood.created_at else None,
        }
        for mood in recent_moods
    ]
    activity_lines = [
        {
            "activity_name": activity.activity_name,
            "activity_category": activity.activity_category,
            "value": activity.value,
            "unit": activity.unit,
            "duration_minutes": activity.duration_minutes,
            "notes": activity.notes,
            "created_at": activity.created_at.isoformat() if activity.created_at else None,
        }
        for activity in recent_activities
    ]

    return {
        "recent_conversation": message_lines,
        "recent_moods": mood_lines,
        "recent_activities": activity_lines,
        "challenge_summary": challenge_summary,
    }


def get_challenge_summary_tool(db, user_id: int) -> dict:
    return challenge_service.get_summary(db=db, user_id=user_id)
