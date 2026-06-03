from datetime import date, datetime

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.db_models import ActivityLog


class ActivityRepository:
    def create_activity_log(
        self,
        db: Session,
        user_id: int,
        activity_category: str,
        activity_name: str,
        value: int | None = None,
        unit: str | None = None,
        duration_minutes: int | None = None,
        notes: str | None = None,
        calories_burned: int | None = None,
        steps_count: int | None = None,
        intensity_level: str | None = None,
        created_at: datetime | None = None,
    ) -> ActivityLog:
        activity_log = ActivityLog(
            user_id=user_id,
            activity_category=activity_category,
            activity_name=activity_name,
            value=value,
            unit=unit,
            duration_minutes=duration_minutes,
            notes=notes,
            calories_burned=calories_burned,
            steps_count=steps_count,
            intensity_level=intensity_level,
            created_at=created_at,
        )
        db.add(activity_log)
        db.commit()
        db.refresh(activity_log)
        return activity_log

    def update_activity_log(
        self,
        db: Session,
        activity_log: ActivityLog,
        *,
        value: int | None = None,
        unit: str | None = None,
        duration_minutes: int | None = None,
        notes: str | None = None,
    ) -> ActivityLog:
        activity_log.value = value
        activity_log.unit = unit
        activity_log.duration_minutes = duration_minutes
        activity_log.notes = notes
        db.commit()
        db.refresh(activity_log)
        return activity_log

    def get_recent_activities(self, db: Session, user_id: int, limit: int = 5) -> list[ActivityLog]:
        return (
            db.query(ActivityLog)
            .filter(ActivityLog.user_id == user_id)
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
            .all()
        )

    def list_activities_for_day(self, db: Session, user_id: int, day: date | None = None) -> list[ActivityLog]:
        day = day or date.today()
        return (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user_id,
                func.date(ActivityLog.created_at) == day.isoformat(),
            )
            .order_by(desc(ActivityLog.created_at))
            .all()
        )

    def list_activities_between(self, db: Session, user_id: int, start_day: date, end_day: date) -> list[ActivityLog]:
        return (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user_id,
                func.date(ActivityLog.created_at) >= start_day.isoformat(),
                func.date(ActivityLog.created_at) <= end_day.isoformat(),
            )
            .order_by(desc(ActivityLog.created_at))
            .all()
        )

    def get_latest_activity_for_day(self, db: Session, user_id: int, activity_name: str, day: date | None = None) -> ActivityLog | None:
        day = day or date.today()
        return (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.activity_name == activity_name,
                func.date(ActivityLog.created_at) == day.isoformat(),
            )
            .order_by(desc(ActivityLog.created_at))
            .first()
        )

    def get_total_value_for_day(self, db: Session, user_id: int, activity_name: str, day: date | None = None) -> int:
        day = day or date.today()
        total = (
            db.query(func.coalesce(func.sum(ActivityLog.value), 0))
            .filter(
                ActivityLog.user_id == user_id,
                ActivityLog.activity_name == activity_name,
                func.date(ActivityLog.created_at) == day.isoformat(),
            )
            .scalar()
        )
        return int(total or 0)
