from __future__ import annotations

from datetime import datetime
from datetime import date

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.db_models import ChallengeEvent, ChallengeReminder, ChallengeTemplate, PointLedger, UserChallenge


class ChallengeRepository:
    def get_template_by_code(self, db: Session, code: str) -> ChallengeTemplate | None:
        return db.query(ChallengeTemplate).filter(ChallengeTemplate.code == code).first()

    def get_template_by_id(self, db: Session, template_id: int) -> ChallengeTemplate | None:
        return db.query(ChallengeTemplate).filter(ChallengeTemplate.id == template_id).first()

    def list_active_templates(self, db: Session) -> list[ChallengeTemplate]:
        return (
            db.query(ChallengeTemplate)
            .filter(ChallengeTemplate.is_active == 1)
            .order_by(ChallengeTemplate.id.asc())
            .all()
        )

    def upsert_template(
        self,
        db: Session,
        *,
        code: str,
        name: str,
        description: str,
        metric_key: str,
        goal_value: int,
        unit: str | None = None,
        points: int = 50,
        reminder_message: str | None = None,
        is_active: int = 1,
    ) -> ChallengeTemplate:
        record = self.get_template_by_code(db=db, code=code)
        if record:
            record.name = name
            record.description = description
            record.metric_key = metric_key
            record.goal_value = goal_value
            record.unit = unit
            record.points = points
            record.reminder_message = reminder_message
            record.is_active = is_active
        else:
            record = ChallengeTemplate(
                code=code,
                name=name,
                description=description,
                metric_key=metric_key,
                goal_value=goal_value,
                unit=unit,
                points=points,
                reminder_message=reminder_message,
                is_active=is_active,
            )
            db.add(record)

        db.commit()
        db.refresh(record)
        return record

    def get_user_challenge(
        self,
        db: Session,
        *,
        user_id: int,
        template_id: int,
        week_start: date,
        week_end: date,
    ) -> UserChallenge | None:
        return (
            db.query(UserChallenge)
            .filter(
                UserChallenge.user_id == user_id,
                UserChallenge.template_id == template_id,
                UserChallenge.week_start == week_start,
                UserChallenge.week_end == week_end,
            )
            .first()
        )

    def list_user_challenges(self, db: Session, *, user_id: int, week_start: date, week_end: date) -> list[UserChallenge]:
        return (
            db.query(UserChallenge)
            .filter(
                UserChallenge.user_id == user_id,
                UserChallenge.week_start == week_start,
                UserChallenge.week_end == week_end,
            )
            .order_by(UserChallenge.id.asc())
            .all()
        )

    def list_user_challenges_active_on(self, db: Session, *, user_id: int, active_date: date) -> list[UserChallenge]:
        return (
            db.query(UserChallenge)
            .filter(
                UserChallenge.user_id == user_id,
                UserChallenge.week_start <= active_date,
                UserChallenge.week_end >= active_date,
            )
            .order_by(UserChallenge.id.asc())
            .all()
        )

    def get_user_challenge_for_metric(
        self,
        db: Session,
        *,
        user_id: int,
        metric_key: str,
        active_date: date,
        prefer_demo: bool = True,
    ) -> UserChallenge | None:
        challenges = self.list_user_challenges_active_on(db=db, user_id=user_id, active_date=active_date)
        metric_key = metric_key.strip().lower()

        matched = []
        for challenge in challenges:
            template = self.get_template_by_id(db=db, template_id=challenge.template_id)
            if not template:
                continue
            if template.metric_key != metric_key:
                continue
            matched.append((template.code, challenge))

        if not matched:
            return None

        if prefer_demo:
            demo_match = next((challenge for code, challenge in matched if code.startswith("demo_")), None)
            if demo_match:
                return demo_match

        return matched[0][1]

    def upsert_user_challenge(
        self,
        db: Session,
        *,
        user_id: int,
        template: ChallengeTemplate,
        week_start: date,
        week_end: date,
    ) -> UserChallenge:
        record = self.get_user_challenge(
            db=db,
            user_id=user_id,
            template_id=template.id,
            week_start=week_start,
            week_end=week_end,
        )
        if record:
            record.goal_value = template.goal_value
        else:
            record = UserChallenge(
                user_id=user_id,
                template_id=template.id,
                week_start=week_start,
                week_end=week_end,
                status="active",
                progress_value=0,
                goal_value=template.goal_value,
                points_awarded=0,
                payload_json="{}",
            )
            db.add(record)

        db.commit()
        db.refresh(record)
        return record

    def update_user_challenge(self, db: Session, challenge: UserChallenge) -> UserChallenge:
        db.commit()
        db.refresh(challenge)
        return challenge

    def create_event(
        self,
        db: Session,
        *,
        user_id: int,
        user_challenge_id: int | None,
        event_type: str,
        value: int | None = None,
        message: str | None = None,
        metadata_json: str = "{}",
    ) -> ChallengeEvent:
        event = ChallengeEvent(
            user_id=user_id,
            user_challenge_id=user_challenge_id,
            event_type=event_type,
            value=value,
            message=message,
            metadata_json=metadata_json,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def create_point_entry(
        self,
        db: Session,
        *,
        user_id: int,
        source_type: str,
        source_id: int | None,
        points: int,
        note: str | None = None,
    ) -> PointLedger:
        entry = PointLedger(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            points=points,
            note=note,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def get_total_points(self, db: Session, *, user_id: int) -> int:
        total = (
            db.query(func.coalesce(func.sum(PointLedger.points), 0))
            .filter(PointLedger.user_id == user_id)
            .scalar()
        )
        return int(total or 0)

    def get_weekly_points(self, db: Session, *, user_id: int, week_start: date, week_end: date) -> int:
        """Get points earned in a specific week"""
        from sqlalchemy import and_
        from datetime import datetime, time
        
        # Convert dates to datetime bounds
        week_start_dt = datetime.combine(week_start, time.min)
        week_end_dt = datetime.combine(week_end, time.max)
        
        total = (
            db.query(func.coalesce(func.sum(PointLedger.points), 0))
            .filter(
                and_(
                    PointLedger.user_id == user_id,
                    PointLedger.created_at >= week_start_dt,
                    PointLedger.created_at <= week_end_dt
                )
            )
            .scalar()
        )
        return int(total or 0)

    def list_reminders(
        self,
        db: Session,
        *,
        user_id: int,
        status: str | None = None,
        limit: int = 20,
        newest_first: bool = True,
    ) -> list[ChallengeReminder]:
        query = db.query(ChallengeReminder).filter(ChallengeReminder.user_id == user_id)
        if status:
            query = query.filter(ChallengeReminder.status == status)
        sort_key = func.coalesce(ChallengeReminder.sent_at, ChallengeReminder.created_at)
        order_clause = desc(sort_key) if newest_first else sort_key.asc()
        return query.order_by(order_clause).limit(limit).all()

    def get_reminder_by_id(self, db: Session, *, reminder_id: int, user_id: int | None = None) -> ChallengeReminder | None:
        query = db.query(ChallengeReminder).filter(ChallengeReminder.id == reminder_id)
        if user_id is not None:
            query = query.filter(ChallengeReminder.user_id == user_id)
        return query.first()

    def create_reminder(
        self,
        db: Session,
        *,
        user_id: int,
        user_challenge_id: int | None,
        reminder_type: str,
        message: str,
        status: str = "pending",
    ) -> ChallengeReminder:
        reminder = ChallengeReminder(
            user_id=user_id,
            user_challenge_id=user_challenge_id,
            reminder_type=reminder_type,
            message=message,
            status=status,
            sent_at=datetime.utcnow(),
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder

    def update_reminder(self, db: Session, reminder: ChallengeReminder) -> ChallengeReminder:
        db.commit()
        db.refresh(reminder)
        return reminder
