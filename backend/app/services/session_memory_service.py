from app.repositories.session_summary_repository import SessionSummaryRepository


class SessionMemoryService:
    """Demo-friendly short-term memory using a compact session summary."""

    def __init__(self):
        self.repository = SessionSummaryRepository()

    def get_session_summary(self, db, session_id: int) -> str:
        record = self.repository.get_by_session_id(db=db, session_id=session_id)
        return record.summary_text if record else ""

    def update_session_summary(
        self,
        db,
        session_id: int,
        user_id: int,
        recent_messages: list,
        recent_moods: list,
        recent_activities: list,
    ) -> str:
        summary_text = self._build_summary_text(
            recent_messages=recent_messages,
            recent_moods=recent_moods,
            recent_activities=recent_activities,
        )
        self.repository.upsert_summary(
            db=db,
            session_id=session_id,
            user_id=user_id,
            summary_text=summary_text,
        )
        return summary_text

    def _build_summary_text(self, recent_messages: list, recent_moods: list, recent_activities: list) -> str:
        lines: list[str] = []

        if recent_messages:
            latest_user_message = next((m.message for m in reversed(recent_messages) if m.role == "user"), None)
            if latest_user_message:
                lines.append(f"Latest user focus: {latest_user_message}")

        if recent_moods:
            latest_mood = recent_moods[0]
            reason_part = f" because {latest_mood.reason}" if latest_mood.reason else ""
            lines.append(f"Latest mood: {latest_mood.mood_label}{reason_part}")

        if recent_activities:
            formatted = []
            for activity in recent_activities[:3]:
                details = []
                if activity.value is not None and activity.unit:
                    details.append(f"{activity.value} {activity.unit}")
                if activity.duration_minutes is not None:
                    details.append(f"{activity.duration_minutes} min")
                detail_text = f" ({', '.join(details)})" if details else ""
                formatted.append(f"{activity.activity_name}{detail_text}")
            lines.append("Recent activities: " + ", ".join(formatted))

        if recent_messages:
            unresolved = [m.message for m in reversed(recent_messages[-4:]) if m.role == "user"]
            if unresolved:
                lines.append("Conversation trail: " + " | ".join(unresolved[:2]))

        return "\n".join(lines) if lines else "No session summary yet."
