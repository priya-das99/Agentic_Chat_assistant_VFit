from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
from app.models.db_models import MoodLog


class MoodRepository:
    def create_mood_log(
        self,
        db: Session,
        user_id: int,
        mood_label: str,
        mood_score: int | None = None,
        reason: str | None = None,
    ) -> MoodLog:
        mood_log = MoodLog(
            user_id=user_id,
            mood_label=mood_label,
            mood_score=mood_score,
            reason=reason,
        )
        db.add(mood_log)
        db.commit()
        db.refresh(mood_log)
        return mood_log

    def get_recent_moods(self, db: Session, user_id: int, limit: int = 5) -> list[MoodLog]:
        return (
            db.query(MoodLog)
            .filter(MoodLog.user_id == user_id)
            .order_by(desc(MoodLog.created_at))
            .limit(limit)
            .all()
        )

    def list_moods_for_day(self, db: Session, user_id: int, day: date | None = None) -> list[MoodLog]:
        day = day or date.today()
        return (
            db.query(MoodLog)
            .filter(
                MoodLog.user_id == user_id,
                func.date(MoodLog.created_at) == day.isoformat(),
            )
            .order_by(desc(MoodLog.created_at))
            .all()
        )

    def list_moods_between(self, db: Session, user_id: int, start_day: date, end_day: date) -> list[MoodLog]:
        return (
            db.query(MoodLog)
            .filter(
                MoodLog.user_id == user_id,
                func.date(MoodLog.created_at) >= start_day.isoformat(),
                func.date(MoodLog.created_at) <= end_day.isoformat(),
            )
            .order_by(desc(MoodLog.created_at))
            .all()
        )
