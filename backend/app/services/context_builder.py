from app.repositories.chat_repository import ChatRepository
from app.services.challenge_service import ChallengeService
from app.services.activity_service import ActivityService
from app.services.memory_service import MemoryService
from app.services.mood_service import MoodService
from app.services.profile_service import ProfileService
from app.services.session_memory_service import SessionMemoryService


class ContextBuilder:
    def __init__(self):
        self.chat_repository = ChatRepository()
        self.challenge_service = ChallengeService()
        self.mood_service = MoodService()
        self.activity_service = ActivityService()
        self.profile_service = ProfileService()
        self.memory_service = MemoryService()
        self.session_memory_service = SessionMemoryService()

    def build_context_packet(self, db, user_id: int, session_id: int | None = None) -> str:
        profile = self.profile_service.get_or_create_profile(db=db, user_id=user_id)
        memories = self.memory_service.get_recent_memories(db=db, user_id=user_id, limit=5)
        recent_messages = self.chat_repository.get_recent_messages(db=db, user_id=user_id, limit=6)
        recent_moods = self.mood_service.get_recent_moods(db=db, user_id=user_id, limit=3)
        recent_activities = self.activity_service.get_recent_activities(db=db, user_id=user_id, limit=5)
        challenge_summary = self.challenge_service.get_summary(db=db, user_id=user_id, reference_date=None)
        session_summary = self.session_memory_service.get_session_summary(db=db, session_id=session_id) if session_id else ""

        message_lines = []
        for message in reversed(recent_messages):
            message_lines.append(f"{message.role}: {message.message}")

        mood_lines = []
        for mood in recent_moods:
            reason_part = f" because {mood.reason}" if mood.reason else ""
            mood_lines.append(f"- {mood.mood_label}{reason_part}")

        activity_lines = []
        for activity in recent_activities:
            details = []
            if activity.value is not None and activity.unit:
                details.append(f"{activity.value} {activity.unit}")
            if activity.duration_minutes is not None:
                details.append(f"{activity.duration_minutes} minutes")
            if activity.notes:
                details.append(activity.notes)
            activity_detail = ", ".join(details) if details else "logged"
            activity_lines.append(f"- {activity.activity_name}: {activity_detail}")

        context_parts = [
            "User profile:\n" + self.profile_service.format_profile_summary(profile),
            "Persistent memory:\n" + self.memory_service.format_memory_summary(memories),
            "Session summary:\n" + (session_summary or "No session summary yet."),
            "Recent conversation:\n" + ("\n".join(message_lines) if message_lines else "No recent messages."),
            "Recent moods:\n" + ("\n".join(mood_lines) if mood_lines else "No recent moods."),
            "Recent activities:\n" + ("\n".join(activity_lines) if activity_lines else "No recent activities."),
            "Weekly challenges:\n" + self.challenge_service.format_summary_text(challenge_summary),
        ]

        return "\n\n".join(context_parts)
