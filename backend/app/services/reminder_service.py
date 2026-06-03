from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db_models import ActivityLog, ChallengeReminder, MoodLog, User
from app.repositories.challenge_repository import ChallengeRepository
from app.services.activity_service import ActivityService
from app.services.challenge_service import ChallengeService


LOCAL_TZ = ZoneInfo("Asia/Kolkata")
logger = logging.getLogger(__name__)


@dataclass
class ReminderCandidate:
    reminder_type: str
    message: str
    source: str
    user_challenge_id: int | None = None


class ReminderService:
    MAX_REMINDERS_PER_DAY = 2
    MIN_REMINDER_GAP_HOURS = 4

    def __init__(self):
        self.challenge_service = ChallengeService()
        self.challenge_repository = ChallengeRepository()
        self.activity_service = ActivityService()

    def run_cycle(self, db: Session, now: datetime | None = None) -> list[dict]:
        now = now.astimezone(LOCAL_TZ) if now and now.tzinfo else datetime.now(LOCAL_TZ)
        created: list[dict] = []
        logger.info("Reminder cycle started at %s", now.isoformat())
        for user_id in self._list_user_ids(db=db):
            reminder = self.ensure_user_reminder(db=db, user_id=user_id, now=now)
            if reminder:
                created.append(reminder)
                logger.info(
                    "Reminder created for user_id=%s type=%s reminder_id=%s",
                    user_id,
                    reminder.get("reminder_type"),
                    reminder.get("reminder_id"),
                )
        logger.info("Reminder cycle finished: created=%s", len(created))
        return created

    def ensure_user_reminder(self, db: Session, user_id: int, now: datetime | None = None) -> dict | None:
        now = now.astimezone(LOCAL_TZ) if now and now.tzinfo else datetime.now(LOCAL_TZ)
        self.challenge_service.get_reminders(db=db, user_id=user_id, reference_date=now.date())

        if self._has_pending_reminder(db=db, user_id=user_id):
            logger.info("Skipping user_id=%s because a pending reminder already exists", user_id)
            return None

        if self._count_reminders_today(db=db, user_id=user_id, now=now) >= self.MAX_REMINDERS_PER_DAY:
            logger.info("Skipping user_id=%s because daily reminder limit was reached", user_id)
            return None

        if self._recent_any_reminder(db=db, user_id=user_id, hours=self.MIN_REMINDER_GAP_HOURS):
            logger.info(
                "Skipping user_id=%s because a reminder was handled recently (cooldown=%sh)",
                user_id,
                self.MIN_REMINDER_GAP_HOURS,
            )
            return None

        candidate = self._build_candidate(db=db, user_id=user_id, now=now)
        if not candidate:
            logger.info("Skipping user_id=%s because no reminder candidate matched", user_id)
            return None

        if self._recent_same_type(db=db, user_id=user_id, reminder_type=candidate.reminder_type, hours=12):
            logger.info(
                "Skipping user_id=%s because reminder type %s was already sent recently",
                user_id,
                candidate.reminder_type,
            )
            return None

        reminder = self.challenge_repository.create_reminder(
            db=db,
            user_id=user_id,
            user_challenge_id=candidate.user_challenge_id,
            reminder_type=candidate.reminder_type,
            message=candidate.message,
            status="pending",
        )
        return self.challenge_service._reminder_to_dict(reminder)

    def _build_candidate(self, db: Session, user_id: int, now: datetime) -> ReminderCandidate | None:
        hour = now.hour
        today = now.date()
        active_challenges = self.challenge_repository.list_user_challenges_active_on(
            db=db,
            user_id=user_id,
            active_date=today,
        )
        incomplete = next((challenge for challenge in active_challenges if challenge.status != "completed"), None)
        incomplete_name = None
        incomplete_id = None
        if incomplete:
            template = self.challenge_repository.get_template_by_id(db=db, template_id=incomplete.template_id)
            incomplete_name = template.name if template else "your challenge"
            incomplete_id = incomplete.id

        if 7 <= hour < 11:
            if not self._has_mood_today(db=db, user_id=user_id, day=today):
                return ReminderCandidate(
                    reminder_type="mood",
                    message="Morning check-in time. A quick mood log helps me keep your day personalized.",
                    source="schedule",
                )
            if not self._has_water_today(db=db, user_id=user_id, day=today):
                return ReminderCandidate(
                    reminder_type="water",
                    message="It’s a good time for a water check. Small sips still count.",
                    source="schedule",
                )

        if 12 <= hour < 17:
            if not self._has_activity_today(db=db, user_id=user_id, day=today):
                return ReminderCandidate(
                    reminder_type="activity",
                    message="Midday is a nice time to log a small activity and keep your momentum going.",
                    source="schedule",
                )
            if not self._has_water_today(db=db, user_id=user_id, day=today):
                return ReminderCandidate(
                    reminder_type="water",
                    message="Quick hydration check: want to log a glass of water?",
                    source="schedule",
                )

        if 19 <= hour < 23:
            if not self._has_sleep_today(db=db, user_id=user_id, day=today):
                return ReminderCandidate(
                    reminder_type="sleep",
                    message="Evening check-in: logging sleep now will help keep your streak strong.",
                    source="schedule",
                )
            if incomplete:
                return ReminderCandidate(
                    reminder_type="challenge",
                    message=f"You're still building on {incomplete_name}. One small step can move it forward tonight.",
                    source="schedule",
                    user_challenge_id=incomplete_id,
                )

        if incomplete:
            return ReminderCandidate(
                reminder_type="challenge",
                message=f"You're making progress on {incomplete_name}. A quick check-in could keep the streak alive.",
                source="schedule",
                user_challenge_id=incomplete_id,
            )

        return None

    def _has_mood_today(self, db: Session, user_id: int, day: date) -> bool:
        return (
            db.query(MoodLog.id)
            .filter(
                MoodLog.user_id == user_id,
                func.date(MoodLog.created_at) == day.isoformat(),
            )
            .first()
            is not None
        )

    def _has_water_today(self, db: Session, user_id: int, day: date) -> bool:
        return self.activity_service.get_total_value_for_day(db=db, user_id=user_id, activity_name="water", day=day) > 0

    def _has_sleep_today(self, db: Session, user_id: int, day: date) -> bool:
        return self.activity_service.get_latest_activity_for_day(db=db, user_id=user_id, activity_name="sleep", day=day) is not None

    def _has_activity_today(self, db: Session, user_id: int, day: date) -> bool:
        return (
            db.query(ActivityLog.id)
            .filter(
                ActivityLog.user_id == user_id,
                func.date(ActivityLog.created_at) == day.isoformat(),
                ActivityLog.activity_category == "exercise",
            )
            .first()
            is not None
        )

    def _has_pending_reminder(self, db: Session, user_id: int) -> bool:
        return (
            db.query(ChallengeReminder.id)
            .filter(ChallengeReminder.user_id == user_id, ChallengeReminder.status == "pending")
            .first()
            is not None
        )

    def _count_reminders_today(self, db: Session, user_id: int, now: datetime) -> int:
        local_day = now.date().isoformat()
        return (
            db.query(ChallengeReminder.id)
            .filter(
                ChallengeReminder.user_id == user_id,
                func.date(ChallengeReminder.created_at) == local_day,
            )
            .count()
        )

    def _recent_same_type(self, db: Session, user_id: int, reminder_type: str, hours: int = 12) -> bool:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return (
            db.query(ChallengeReminder.id)
            .filter(
                ChallengeReminder.user_id == user_id,
                ChallengeReminder.reminder_type == reminder_type,
                ChallengeReminder.created_at >= cutoff,
            )
            .first()
            is not None
        )

    def _recent_any_reminder(self, db: Session, user_id: int, hours: int = 4) -> bool:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return (
            db.query(ChallengeReminder.id)
            .filter(
                ChallengeReminder.user_id == user_id,
                ChallengeReminder.created_at >= cutoff,
            )
            .first()
            is not None
        )

    def _list_user_ids(self, db: Session) -> list[int]:
        user_ids = [row[0] for row in db.query(User.id).order_by(User.id.asc()).all()]
        return user_ids
