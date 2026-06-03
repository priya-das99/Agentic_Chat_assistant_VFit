from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from app.models.db_models import ChallengeReminder, ChallengeTemplate, UserChallenge
from app.repositories.challenge_repository import ChallengeRepository


class ChallengeService:
    ACTIVE_REMINDER_TTL_HOURS = 12

    DEFAULT_TEMPLATES = [
        {
            "code": "demo_mood_3d",
            "name": "3-Day Mood Logging Demo",
            "description": "Log your mood once a day for 3 days in a row.",
            "metric_key": "mood",
            "goal_value": 3,
            "unit": "days",
            "points": 25,
            "reminder_message": "A quick mood check-in keeps your 3-day demo streak alive.",
        },
        {
            "code": "demo_sleep_3d",
            "name": "3-Day Sleep Logging Demo",
            "description": "Log your sleep once a day for 3 days in a row.",
            "metric_key": "sleep",
            "goal_value": 3,
            "unit": "days",
            "points": 25,
            "reminder_message": "A sleep log today keeps your 3-day sleep challenge on track.",
        },
        {
            "code": "weekly_steps",
            "name": "3,000 Steps Weekly",
            "description": "Reach 3,000 steps this week to keep your momentum going.",
            "metric_key": "steps",
            "goal_value": 3000,
            "unit": "steps",
            "points": 60,
            "reminder_message": "A short walk can move you closer to your weekly step goal.",
        },
        {
            "code": "weekly_water",
            "name": "Water Intake Challenge",
            "description": "Log water regularly through the week to stay hydrated.",
            "metric_key": "water",
            "goal_value": 7,
            "unit": "logs",
            "points": 40,
            "reminder_message": "A quick water log today keeps your hydration streak alive.",
        },
        {
            "code": "weekly_mood",
            "name": "Mood Logging Challenge",
            "description": "Check in with your mood several times this week.",
            "metric_key": "mood",
            "goal_value": 3,
            "unit": "logs",
            "points": 35,
            "reminder_message": "A mood check-in only takes a moment and helps you stay in tune with yourself.",
        },
        {
            "code": "weekly_activity",
            "name": "Activity Logging Challenge",
            "description": "Log your workouts or active sessions through the week.",
            "metric_key": "activity",
            "goal_value": 3,
            "unit": "logs",
            "points": 50,
            "reminder_message": "One activity log can keep this week moving in the right direction.",
        },
    ]

    def __init__(self):
        self.repository = ChallengeRepository()

    def seed_default_templates(self, db) -> list[ChallengeTemplate]:
        templates: list[ChallengeTemplate] = []
        for template in self.DEFAULT_TEMPLATES:
            templates.append(
                self.repository.upsert_template(
                    db=db,
                    code=template["code"],
                    name=template["name"],
                    description=template["description"],
                    metric_key=template["metric_key"],
                    goal_value=template["goal_value"],
                    unit=template["unit"],
                    points=template["points"],
                    reminder_message=template["reminder_message"],
                )
            )
        return templates

    def ensure_weekly_challenges(self, db, user_id: int, reference_date: date | None = None) -> list[UserChallenge]:
        week_start, week_end = self._get_week_bounds(reference_date or date.today())
        templates = self.seed_default_templates(db=db)
        challenges: list[UserChallenge] = []
        for template in templates:
            challenges.append(
                self.repository.upsert_user_challenge(
                    db=db,
                    user_id=user_id,
                    template=template,
                    week_start=week_start,
                    week_end=week_end,
                )
            )
        return challenges

    def ensure_demo_challenges(self, db, user_id: int, reference_date: date | None = None) -> list[UserChallenge]:
        start_date = reference_date or date.today()
        end_date = start_date + timedelta(days=2)
        demo_templates = [template for template in self.seed_default_templates(db=db) if template.code.startswith("demo_")]
        challenges: list[UserChallenge] = []
        for template in demo_templates:
            challenges.append(
                self.repository.upsert_user_challenge(
                    db=db,
                    user_id=user_id,
                    template=template,
                    week_start=start_date,
                    week_end=end_date,
                )
            )
        return challenges

    def get_current_challenges(self, db, user_id: int, reference_date: date | None = None) -> list[dict]:
        summary = self.get_summary(db=db, user_id=user_id, reference_date=reference_date)
        return summary["active_challenges"]

    def get_templates(self, db) -> list[dict]:
        templates = self.repository.list_active_templates(db=db)
        return [
            {
                "code": template.code,
                "name": template.name,
                "description": template.description,
                "metric_key": template.metric_key,
                "goal_value": template.goal_value,
                "unit": template.unit,
                "points": template.points,
                "reminder_message": template.reminder_message,
            }
            for template in templates
        ]

    def get_summary(self, db, user_id: int, reference_date: date | None = None) -> dict:
        reference_date = reference_date or date.today()
        week_start, week_end = self._get_week_bounds(reference_date)
        self.ensure_weekly_challenges(db=db, user_id=user_id, reference_date=reference_date)
        self.ensure_demo_challenges(db=db, user_id=user_id, reference_date=reference_date)
        challenges = self.repository.list_user_challenges_active_on(db=db, user_id=user_id, active_date=reference_date)
        challenges = self._dedupe_active_challenges(db=db, challenges=challenges)
        reminders = self.get_reminders(db=db, user_id=user_id, reference_date=reference_date)
        total_points = self.repository.get_total_points(db=db, user_id=user_id)
        weekly_points = self.repository.get_weekly_points(db=db, user_id=user_id, week_start=week_start, week_end=week_end)

        challenge_items = [self._challenge_to_dict(db=db, challenge=challenge) for challenge in challenges]
        return {
            "user_id": user_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_points": total_points,
            "weekly_points": weekly_points,
            "active_challenges": challenge_items,
            "reminders": reminders,
            "message": self._build_summary_message(challenge_items, total_points),
        }

    def record_signal(
        self,
        db,
        *,
        user_id: int,
        metric_key: str,
        challenge_code: str | None = None,
        value: int | None = None,
        message: str | None = None,
        metadata: dict | None = None,
        reference_date: date | None = None,
    ) -> dict:
        reference_date = reference_date or date.today()
        week_start, week_end = self._get_week_bounds(reference_date)
        self.ensure_weekly_challenges(db=db, user_id=user_id, reference_date=reference_date)
        self.ensure_demo_challenges(db=db, user_id=user_id, reference_date=reference_date)
        template = self._get_template_for_signal(db=db, metric_key=metric_key, challenge_code=challenge_code)
        if not template:
            return {"updated": False, "reason": "template_not_found"}

        challenge = self.repository.get_user_challenge_for_metric(
            db=db,
            user_id=user_id,
            metric_key=template.metric_key,
            active_date=reference_date,
        )
        if not challenge:
            challenge = self.repository.upsert_user_challenge(
                db=db,
                user_id=user_id,
                template=template,
                week_start=week_start,
                week_end=week_end,
            )

        increment = self._resolve_increment(metric_key=metric_key, value=value)
        challenge.progress_value = int(challenge.progress_value or 0) + increment
        challenge.last_event_at = datetime.utcnow()
        celebration = None
        badge_name = None
        if challenge.progress_value >= challenge.goal_value and challenge.status != "completed":
            challenge.status = "completed"
            challenge.completed_at = datetime.utcnow()
            if challenge.points_awarded < template.points:
                challenge.points_awarded = template.points
                self.repository.create_point_entry(
                    db=db,
                    user_id=user_id,
                    source_type="challenge_completion",
                    source_id=challenge.id,
                    points=template.points,
                    note=f"Completed challenge {template.code}",
                )
            badge_name = self._badge_name_for_template(template)
            celebration = f"🎉 Challenge complete! Badge unlocked: {badge_name}."

        self.repository.update_user_challenge(db=db, challenge=challenge)
        event = self.repository.create_event(
            db=db,
            user_id=user_id,
            user_challenge_id=challenge.id,
            event_type=metric_key,
            value=value,
            message=message,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=True),
        )
        return {
            "updated": True,
            "challenge": self._challenge_to_dict(db=db, challenge=challenge),
            "event_id": event.id,
            "celebration": celebration,
            "badge_name": badge_name,
        }

    def record_mood_event(self, db, *, user_id: int, message: str | None = None) -> dict:
        return self.record_signal(db=db, user_id=user_id, metric_key="mood", value=1, message=message, metadata={"source": "mood"})

    def record_activity_event(self, db, *, user_id: int, activity_name: str | None = None, duration_minutes: int | None = None, message: str | None = None) -> dict:
        metadata = {"source": "activity"}
        if activity_name:
            metadata["activity_name"] = activity_name
        if duration_minutes is not None:
            metadata["duration_minutes"] = duration_minutes
        return self.record_signal(db=db, user_id=user_id, metric_key="activity", value=1, message=message, metadata=metadata)

    def record_water_event(self, db, *, user_id: int, value: int | None = None, message: str | None = None) -> dict:
        metadata = {"source": "water"}
        if value is not None:
            metadata["logged_value"] = value
        return self.record_signal(db=db, user_id=user_id, metric_key="water", value=1, message=message, metadata=metadata)

    def record_sleep_event(self, db, *, user_id: int, duration_minutes: int | None = None, message: str | None = None) -> dict:
        metadata = {"source": "sleep"}
        if duration_minutes is not None:
            metadata["duration_minutes"] = duration_minutes
        return self.record_signal(db=db, user_id=user_id, metric_key="sleep", value=1, message=message, metadata=metadata)

    def record_step_progress(self, db, *, user_id: int, steps: int, message: str | None = None) -> dict:
        return self.record_signal(
            db=db,
            user_id=user_id,
            metric_key="steps",
            value=steps,
            message=message,
            metadata={"source": "manual_steps", "steps": steps},
        )

    def get_reminders(self, db, user_id: int, reference_date: date | None = None) -> list[dict]:
        reference_date = reference_date or date.today()
        self.ensure_weekly_challenges(db=db, user_id=user_id, reference_date=reference_date)
        self.ensure_demo_challenges(db=db, user_id=user_id, reference_date=reference_date)
        self._promote_due_reminders(db=db, user_id=user_id)
        active = self._normalize_pending_reminders(db=db, user_id=user_id)
        return [self._reminder_to_dict(reminder) for reminder in active]

    def complete_reminder(self, db, reminder_id: int, user_id: int) -> dict | None:
        reminder = self.repository.get_reminder_by_id(db=db, reminder_id=reminder_id, user_id=user_id)
        if not reminder:
            return None
        reminder.status = "completed"
        reminder.sent_at = reminder.sent_at or datetime.utcnow()
        reminder.due_at = None
        self.repository.update_reminder(db=db, reminder=reminder)
        return self._reminder_to_dict(reminder)

    def dismiss_reminder(self, db, reminder_id: int, user_id: int) -> dict | None:
        reminder = self.repository.get_reminder_by_id(db=db, reminder_id=reminder_id, user_id=user_id)
        if not reminder:
            return None
        reminder.status = "dismissed"
        reminder.due_at = None
        self.repository.update_reminder(db=db, reminder=reminder)
        return self._reminder_to_dict(reminder)

    def snooze_reminder(self, db, reminder_id: int, user_id: int, snooze_minutes: int = 30) -> dict | None:
        reminder = self.repository.get_reminder_by_id(db=db, reminder_id=reminder_id, user_id=user_id)
        if not reminder:
            return None
        delay = max(int(snooze_minutes or 30), 5)
        reminder.status = "snoozed"
        reminder.due_at = datetime.utcnow() + timedelta(minutes=delay)
        self.repository.update_reminder(db=db, reminder=reminder)
        return self._reminder_to_dict(reminder)

    def build_motivational_reply(self, db, user_id: int, reference_date: date | None = None) -> str:
        summary = self.get_summary(db=db, user_id=user_id, reference_date=reference_date)
        reminders = summary.get("reminders", [])
        if reminders:
            return reminders[0]["message"]
        return summary["message"]

    def build_chat_reply(self, db, user_id: int, message: str, reference_date: date | None = None) -> str:
        reference_date = reference_date or date.today()
        text = message.strip().lower()
        snapshot = self.get_coach_snapshot(db=db, user_id=user_id, message=message, reference_date=reference_date)
        summary_text = snapshot.get("summary_text") or self.format_chat_summary_text(snapshot)

        if "today" in text:
            reply = f"{snapshot['opener']}\n{summary_text}"
        else:
            reply = f"{snapshot['opener']}\n{summary_text}"

        reminders = self.get_demo_summary(db=db, user_id=user_id, reference_date=reference_date).get("reminders", [])
        if reminders and ("reminder" in text or "motivate" in text or "help" in text):
            reply += f"\n{reminders[0]['message']}"

        if snapshot.get("celebration"):
            reply += f"\n{snapshot['celebration']}"
        reply += f"\n{snapshot['encouragement']}"
        if snapshot.get("next_step") and ("reminder" in text or "motivate" in text or "help" in text):
            reply += f"\n{snapshot['next_step']}"

        return reply

    def get_coach_snapshot(self, db, user_id: int, message: str, reference_date: date | None = None) -> dict:
        reference_date = reference_date or date.today()
        demo_summary = self.get_demo_summary(db=db, user_id=user_id, reference_date=reference_date)
        challenges = demo_summary.get("active_challenges", [])
        total_points = demo_summary.get("total_points", 0)
        completed = sum(1 for challenge in challenges if challenge.get("status") == "completed")
        total = len(challenges)
        progress_text = demo_summary.get("summary_text") or self.format_chat_summary_text(demo_summary)
        badge_name = None
        celebration = None

        if completed == 0:
            encouragement = "One small check-in is a great first win."
            opener = "Let’s get a quick win on the board. 💪"
        elif completed < total:
            encouragement = "Nice progress. You’re building momentum one step at a time."
            opener = "You’re building a real streak. 🔥"
        else:
            badge_name = "Momentum Star"
            celebration = f"🎉 Challenge complete! Badge unlocked: {badge_name}."
            encouragement = "Great work. That’s the kind of consistency that really sticks."
            opener = "Boom. You crushed it today. 🏅"

        next_step = "Keep going today with one quick check-in."
        reminders = demo_summary.get("reminders", [])
        if "reminder" in message.lower() or "motivate" in message.lower() or "help" in message.lower():
            if reminders:
                next_step = reminders[0]["message"]
            elif completed == total and total > 0:
                next_step = "Celebrate the win, then keep the rhythm going tomorrow."

        return {
            "opener": opener,
            "summary_text": progress_text,
            "encouragement": encouragement,
            "next_step": next_step,
            "points": total_points,
            "completed": completed,
            "total": total,
            "celebration": celebration,
            "badge_name": badge_name,
        }

    def get_demo_summary(self, db, user_id: int, reference_date: date | None = None) -> dict:
        reference_date = reference_date or date.today()
        self.ensure_demo_challenges(db=db, user_id=user_id, reference_date=reference_date)
        challenges = self._list_demo_challenges(db=db, user_id=user_id, reference_date=reference_date)
        challenges = self._dedupe_active_challenges(db=db, challenges=challenges)
        total_points = self.repository.get_total_points(db=db, user_id=user_id)
        challenge_items = [self._challenge_to_dict(db=db, challenge=challenge) for challenge in challenges]
        return {
            "user_id": user_id,
            "week_start": reference_date.isoformat(),
            "week_end": (reference_date + timedelta(days=2)).isoformat(),
            "total_points": total_points,
            "active_challenges": challenge_items,
            "reminders": self.get_reminders(db=db, user_id=user_id, reference_date=reference_date),
            "message": self._build_summary_message(challenge_items, total_points),
            "summary_text": self.format_chat_summary_text({
                "active_challenges": challenge_items,
                "total_points": total_points,
            }),
        }

    def _list_demo_challenges(self, db, user_id: int, reference_date: date) -> list[UserChallenge]:
        active = self.repository.list_user_challenges_active_on(db=db, user_id=user_id, active_date=reference_date)
        demo_challenges: list[UserChallenge] = []
        for challenge in active:
            template = self.repository.get_template_by_id(db=db, template_id=challenge.template_id)
            if template and template.code.startswith("demo_"):
                demo_challenges.append(challenge)
        return demo_challenges

    def _dedupe_active_challenges(self, db, challenges: list[UserChallenge]) -> list[UserChallenge]:
        deduped: dict[str, UserChallenge] = {}
        for challenge in challenges:
            template = self.repository.get_template_by_id(db=db, template_id=challenge.template_id)
            key = template.code if template else str(challenge.template_id)
            current = deduped.get(key)
            if current is None:
                deduped[key] = challenge
                continue

            current_progress = int(current.progress_value or 0)
            incoming_progress = int(challenge.progress_value or 0)
            current_completed = current.status == "completed"
            incoming_completed = challenge.status == "completed"

            if incoming_completed and not current_completed:
                deduped[key] = challenge
            elif incoming_progress > current_progress:
                deduped[key] = challenge
            elif incoming_progress == current_progress and challenge.id > current.id:
                deduped[key] = challenge

        return list(deduped.values())

    def format_summary_text(self, summary: dict) -> str:
        challenge_parts = []
        for challenge in summary.get("active_challenges", []):
            challenge_parts.append(
                f"{challenge['name']}: {challenge['progress_value']}/{challenge['goal_value']}"
            )
        if not challenge_parts:
            return "No active challenges yet."
        return f"{summary.get('message', 'Here is your challenge progress.')} " + " | ".join(challenge_parts)

    def format_chat_summary_text(self, summary: dict) -> str:
        challenges = summary.get("active_challenges", [])
        total_points = summary.get("total_points", 0)
        if not challenges:
            return "No active challenges yet."

        emoji_map = {
            "mood": "😊",
            "sleep": "😴",
            "steps": "👣",
            "water": "💧",
            "activity": "🏃",
        }

        lines = [f"🏅 Points: {total_points}"]
        for challenge in challenges:
            name = challenge["name"]
            progress = challenge["progress_value"]
            goal = challenge["goal_value"]
            metric = (challenge.get("metric_key") or "").lower()
            emoji = emoji_map.get(metric, "✨")
            lines.append(f"{emoji} {name}: {progress}/{goal}")
        return "\n".join(lines)

    def _badge_name_for_template(self, template: ChallengeTemplate | None) -> str:
        if not template:
            return "Momentum Star"

        metric = (template.metric_key or "").lower()
        badge_map = {
            "mood": "Mood Momentum",
            "sleep": "Sleep Streak",
            "water": "Hydration Hero",
            "activity": "Activity Spark",
            "steps": "Step Sprinter",
        }
        return badge_map.get(metric, "Momentum Star")

    def _get_template_for_metric(self, db, metric_key: str) -> ChallengeTemplate | None:
        normalized_metric = metric_key.strip().lower()
        for template in self.repository.list_active_templates(db=db):
            if template.metric_key == normalized_metric:
                return template
        return None

    def _get_template_for_signal(self, db, metric_key: str, challenge_code: str | None = None) -> ChallengeTemplate | None:
        template = self._get_template_for_metric(db=db, metric_key=metric_key)
        if template:
            return template

        if challenge_code:
            normalized_code = challenge_code.strip().lower()
            for candidate in self.repository.list_active_templates(db=db):
                if candidate.code == normalized_code:
                    return candidate
        return None

    def _resolve_increment(self, metric_key: str, value: int | None) -> int:
        normalized_metric = metric_key.strip().lower()
        if normalized_metric == "steps":
            return max(int(value or 0), 0)
        return 1

    def _build_reminder_for_challenge(self, db, challenge: UserChallenge, reference_date: date) -> dict | None:
        if challenge.status == "completed":
            return None

        remaining = max(int(challenge.goal_value or 0) - int(challenge.progress_value or 0), 0)
        if remaining == 0:
            return None

        days_left = max((challenge.week_end - reference_date).days, 0)
        ratio = (challenge.progress_value or 0) / challenge.goal_value if challenge.goal_value else 0
        template = self.repository.get_template_by_id(db=db, template_id=challenge.template_id)

        if challenge.last_reminded_at and datetime.utcnow() - challenge.last_reminded_at < timedelta(hours=12):
            return None

        if ratio == 0:
            reminder_type = "starter"
            message = self._reminder_message(template=template, tone="starter")
        elif ratio >= 0.75:
            reminder_type = "near_complete"
            message = self._reminder_message(template=template, tone="near_complete")
        elif days_left <= 2:
            reminder_type = "week_close"
            message = self._reminder_message(template=template, tone="week_close")
        else:
            return None

        return {
            "reminder_type": reminder_type,
            "message": message,
        }

    def _seed_demo_reminder(self, db, user_id: int, reference_date: date) -> dict | None:
        challenges = self._dedupe_active_challenges(
            db=db,
            challenges=self._list_demo_challenges(db=db, user_id=user_id, reference_date=reference_date),
        )
        if not challenges:
            return None

        preferred = next((challenge for challenge in challenges if int(challenge.progress_value or 0) == 0), challenges[0])
        template = self.repository.get_template_by_id(db=db, template_id=preferred.template_id)
        if not template:
            return None

        message = template.reminder_message or self._reminder_message(template=template, tone="starter")
        reminder = self.repository.create_reminder(
            db=db,
            user_id=user_id,
            user_challenge_id=preferred.id,
            reminder_type="demo",
            message=message,
        )
        preferred.last_reminded_at = datetime.utcnow()
        preferred.reminder_count = int(preferred.reminder_count or 0) + 1
        self.repository.update_user_challenge(db=db, challenge=preferred)
        return self._reminder_to_dict(reminder)

    def _promote_due_reminders(self, db, user_id: int) -> None:
        snoozed = self.repository.list_reminders(db=db, user_id=user_id, status="snoozed", limit=20)
        now = datetime.utcnow()
        for reminder in snoozed:
            if reminder.due_at and reminder.due_at <= now:
                reminder.status = "pending"
                reminder.due_at = None
                reminder.sent_at = now
                self.repository.update_reminder(db=db, reminder=reminder)

    def _normalize_pending_reminders(self, db, user_id: int) -> list[ChallengeReminder]:
        pending = self.repository.list_reminders(
            db=db,
            user_id=user_id,
            status="pending",
            limit=20,
            newest_first=True,
        )
        if not pending:
            return []

        stale_cutoff = datetime.utcnow() - timedelta(hours=self.ACTIVE_REMINDER_TTL_HOURS)
        fresh_pending: list[ChallengeReminder] = []

        for reminder in pending:
            active_since = reminder.sent_at or reminder.created_at
            if active_since and active_since < stale_cutoff:
                reminder.status = "dismissed"
                reminder.due_at = None
                self.repository.update_reminder(db=db, reminder=reminder)
                continue
            fresh_pending.append(reminder)

        if not fresh_pending:
            return []

        primary = fresh_pending[0]
        for reminder in fresh_pending[1:]:
            reminder.status = "dismissed"
            reminder.due_at = None
            self.repository.update_reminder(db=db, reminder=reminder)

        return [primary]

    def promote_due_reminders(self, db, user_id: int) -> None:
        self._promote_due_reminders(db=db, user_id=user_id)

    def _reminder_message(self, *, template: ChallengeTemplate | None, tone: str) -> str:
        template_name = template.name if template else "your challenge"
        if tone == "starter":
            return f"Let’s get rolling on {template_name}. Even one small step counts. 💪"
        if tone == "near_complete":
            return f"You’re close to finishing {template_name}. One more push could wrap it up. 🔥"
        if tone == "week_close":
            return f"The week is winding down for {template_name}, but there is still time to make it happen. ⏳"
        return f"Keep going with {template_name}. You are making progress."

    def _challenge_to_dict(self, db, challenge: UserChallenge) -> dict:
        template = self.repository.get_template_by_id(db=db, template_id=challenge.template_id)
        goal_value = int(challenge.goal_value or (template.goal_value if template else 0))
        progress_value = int(challenge.progress_value or 0)
        remaining_value = max(goal_value - progress_value, 0)
        return {
            "challenge_id": challenge.id,
            "code": template.code if template else str(challenge.template_id),
            "name": template.name if template else "Challenge",
            "description": template.description if template else "",
            "metric_key": template.metric_key if template else "",
            "goal_value": goal_value,
            "progress_value": progress_value,
            "remaining_value": remaining_value,
            "status": challenge.status,
            "points_awarded": int(challenge.points_awarded or 0),
            "week_start": challenge.week_start.isoformat(),
            "week_end": challenge.week_end.isoformat(),
            "completed_at": challenge.completed_at.isoformat() if challenge.completed_at else None,
            "last_event_at": challenge.last_event_at.isoformat() if challenge.last_event_at else None,
            "reminder_count": int(challenge.reminder_count or 0),
            "unit": template.unit if template else None,
        }

    def _reminder_to_dict(self, reminder: ChallengeReminder) -> dict:
        return {
            "reminder_id": reminder.id,
            "reminder_type": reminder.reminder_type,
            "message": reminder.message,
            "status": reminder.status,
            "due_at": reminder.due_at.isoformat() if reminder.due_at else None,
            "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
        }

    def _build_summary_message(self, challenge_items: list[dict], total_points: int) -> str:
        if not challenge_items:
            return "No active challenges yet."

        parts = []
        for challenge in challenge_items:
            label = challenge["name"]
            progress = challenge["progress_value"]
            goal = challenge["goal_value"]
            parts.append(f"{label}: {progress}/{goal}")

        return f"Points: {total_points}. " + " | ".join(parts)

    def _get_week_bounds(self, reference_date: date) -> tuple[date, date]:
        week_start = reference_date - timedelta(days=reference_date.weekday())
        week_end = week_start + timedelta(days=6)
        return week_start, week_end
