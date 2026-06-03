import re
from datetime import date, datetime, time, timedelta

from app.config import OPENAI_API_KEY
from app.models.api_models import ActivityDecisionAction, ActivityDecisionResult, ActivityLogInput, ActivityParseResult
from app.repositories.activity_repository import ActivityRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.challenge_service import ChallengeService
from app.services.fitness_calculator import fitness_calculator


class ActivityService:
    CATEGORY_MAP = {
        "water": "hydration",
        "water intake": "hydration",
        "sleep": "sleep",
        "weight": "body_metrics",
        "badminton": "exercise",
        "football": "exercise",
        "walking": "exercise",
        "walk": "exercise",
        "running": "exercise",
        "run": "exercise",
        "gym": "exercise",
        "yoga": "exercise",
        "exercise": "exercise",
        "soccer": "exercise",
        "swimming": "exercise",
        "swim": "exercise",
        "cycling": "exercise",
        "cycle": "exercise",
        "biking": "exercise",
        "bike": "exercise",
    }

    ACTIVITY_ALIASES = {
        "soccer": "football",
        "walk": "walking",
        "walked": "walking",
        "run": "running",
        "ran": "running",
        "workout": "exercise",
        "training": "exercise",
        "jog": "running",
        "jogging": "running",
        "jogged": "running",
        "water intake": "water",
        "weighed": "weight",
        "swim": "swimming",
        "swam": "swimming",
        "cycle": "cycling",
        "cycled": "cycling",
        "bike": "biking",
        "biked": "biking",
    }

    UNIT_ALIASES = {
        "glass": "glasses",
        "glasses": "glasses",
        "cup": "cups",
        "cups": "cups",
        "bottle": "bottles",
        "bottles": "bottles",
        "ml": "ml",
        "liter": "liters",
        "liters": "liters",
        "litre": "liters",
        "litres": "liters",
        "l": "liters",
        "hr": "hours",
        "hrs": "hours",
        "hour": "hours",
        "hours": "hours",
        "min": "minutes",
        "mins": "minutes",
        "minute": "minutes",
        "minutes": "minutes",
        "km": "km",
        "kilometer": "km",
        "kilometers": "km",
        "mile": "miles",
        "miles": "miles",
        "kilogram": "kg",
        "kilograms": "kg",
        "kg": "kg",
        "lb": "lb",
        "lbs": "lb",
        "pound": "lb",
        "pounds": "lb",
    }

    MOOD_WORDS = {"stressed", "anxious", "sad", "happy", "calm", "tired", "low", "good", "bad"}
    WATER_UNITS = ("ml", "glass", "glasses", "cup", "cups", "bottle", "bottles", "liter", "liters", "litre", "litres", "l")
    SLEEP_UNITS = ("hours", "hour", "hrs", "hr")
    WEIGHT_UNITS = ("kg", "kilogram", "kilograms", "lb", "lbs", "pound", "pounds")
    ACTIVITY_NAMES = ("badminton", "football", "soccer", "walking", "walk", "running", "run", "jogging", "jog", "gym", "yoga", "exercise", "workout", "training", "swimming", "swim", "cycling", "cycle", "biking", "bike")

    def __init__(self):
        self.activity_repository = ActivityRepository()
        self.profile_repository = ProfileRepository()
        self.challenge_service = ChallengeService()

    def normalize_activity_name(self, activity_name: str) -> str:
        normalized = activity_name.strip().lower()
        return self.ACTIVITY_ALIASES.get(normalized, normalized)

    def normalize_unit(self, unit: str | None) -> str | None:
        if not unit:
            return None
        normalized = unit.strip().lower()
        return self.UNIT_ALIASES.get(normalized, normalized)

    def infer_category(self, activity_name: str) -> str:
        normalized = self.normalize_activity_name(activity_name)
        return self.CATEGORY_MAP.get(normalized, "exercise")

    def parse_activity_text(self, message: str) -> ActivityParseResult:
        decision = self.analyze_activity_message(message)
        first_activity = next(
            (action for action in decision.actions if action.entity in {"water", "sleep", "weight", "activity"} and action.action in {"log", "update"}),
            None,
        )
        if not first_activity:
            return ActivityParseResult(matched=False)

        data = first_activity.data
        activity_name = data.get("activity_name") or first_activity.entity
        return ActivityParseResult(
            matched=True,
            activity_name=activity_name,
            activity_category=self.infer_category(activity_name),
            value=data.get("value"),
            unit=data.get("unit"),
            duration_minutes=data.get("duration_minutes"),
            notes=data.get("notes"),
        )



    def apply_activity_decision_result(self, db, user_id: int, decision: ActivityDecisionResult | dict) -> dict:
        normalized_decision = ActivityDecisionResult.model_validate(decision) if isinstance(decision, dict) else decision
        applied: list[dict] = []
        skipped: list[dict] = []

        for action in normalized_decision.actions:
            if action.action not in {"log", "update"}:
                skipped.append(
                    {
                        "entity": action.entity,
                        "action": action.action,
                        "reason": "non_mutating_action",
                    }
                )
                continue

            if action.entity == "mood":
                skipped.append(
                    {
                        "entity": action.entity,
                        "action": action.action,
                        "reason": "mood_is_handled_by_mood_agent",
                    }
                )
                continue

            applied.append(self._apply_single_action(db=db, user_id=user_id, action=action))

        return {
            "applied": applied,
            "skipped": skipped,
            "message": f"Applied {len(applied)} action(s); skipped {len(skipped)} action(s).",
        }

    def analyze_activity_message(self, message: str) -> ActivityDecisionResult:
        text = self._normalize_text(message)
        correction_mode = self._is_correction(text)
        logged_for_date, time_context = self._extract_time_context(text)

        return self._analyze_with_rules(
            text=text,
            logged_for_date=logged_for_date,
            time_context=time_context,
            correction_mode=correction_mode,
        )

    def _analyze_with_rules(
        self,
        *,
        text: str,
        logged_for_date: str,
        time_context: str | None,
        correction_mode: bool,
    ) -> ActivityDecisionResult:
        actions: list[ActivityDecisionAction] = []
        actions.extend(self._extract_weight_actions(text, logged_for_date, time_context, correction_mode))
        actions.extend(self._extract_sleep_actions(text, logged_for_date, time_context, correction_mode))
        actions.extend(self._extract_water_actions(text, logged_for_date, time_context, correction_mode))
        actions.extend(self._extract_activity_actions(text, logged_for_date, time_context, correction_mode))
        actions.extend(self._extract_mood_actions(text, logged_for_date, time_context, correction_mode))

        deduped_actions = self._dedupe_actions(actions)
        if not deduped_actions:
            deduped_actions = [ActivityDecisionAction(entity="activity", action="none", data={})]

        clarifications = [
            action.data["question"]
            for action in deduped_actions
            if action.action in {"clarify", "confirm"} and action.data.get("question")
        ]
        return ActivityDecisionResult(
            actions=deduped_actions,
            clarifications=clarifications,
            message=self._build_summary(deduped_actions),
        )

    def _extract_water_actions(
        self,
        text: str,
        logged_for_date: str,
        time_context: str | None,
        correction_mode: bool,
    ) -> list[ActivityDecisionAction]:
        actions: list[ActivityDecisionAction] = []
        hydration_verbs = ("drank", "drink", "drinking", "had", "logged")
        mentions_water = "water" in text or any(verb in text for verb in hydration_verbs)
        if not mentions_water:
            return actions

        quantity_matches = list(
            re.finditer(
                r"(\d+(?:\.\d+)?)\s*(ml|glass|glasses|cup|cups|bottle|bottles|liter|liters|litre|litres|l)\b",
                text,
            )
        )
        if not quantity_matches:
            if any(phrase in text for phrase in ["some water", "drank water", "drink water", "had water", "water intake"]):
                actions.append(
                    ActivityDecisionAction(
                        entity="water",
                        action="clarify",
                        data={"question": "How much water should I log? Please include ml, liters, glasses, cups, or bottles."},
                    )
                )
            return actions

        for match in quantity_matches:
            raw_value = float(match.group(1))
            unit = self.normalize_unit(match.group(2))
            amount_ml = self._convert_water_to_ml(raw_value, unit)
            data = {
                "activity_name": "water",
                "value": amount_ml,
                "unit": "ml",
                "display_value": raw_value,
                "display_unit": unit,
                "logged_for_date": logged_for_date,
                "time_context": time_context,
            }
            if amount_ml > 10000:
                actions.append(
                    ActivityDecisionAction(
                        entity="water",
                        action="confirm",
                        data={
                            **data,
                            "question": f"{raw_value:g} {unit} of water is unusually high. Do you want me to log it anyway?",
                        },
                    )
                )
            else:
                actions.append(ActivityDecisionAction(entity="water", action="update" if correction_mode else "log", data=data))
        return actions

    def _extract_sleep_actions(
        self,
        text: str,
        logged_for_date: str,
        time_context: str | None,
        correction_mode: bool,
    ) -> list[ActivityDecisionAction]:
        actions: list[ActivityDecisionAction] = []
        if "sleep" not in text and "slept" not in text:
            return actions

        range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(hours|hour|hrs|hr)\b", text)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            avg = round((low + high) / 2, 1)
            data = {
                "activity_name": "sleep",
                "value": avg,
                "unit": "hours",
                "duration_minutes": int(avg * 60),
                "logged_for_date": logged_for_date,
                "time_context": time_context,
                "notes": f"Approximate sleep range: {low:g}-{high:g} hours",
            }
            if avg > 16:
                actions.append(
                    ActivityDecisionAction(
                        entity="sleep",
                        action="confirm",
                        data={**data, "question": f"{avg:g} hours of sleep is unusually high. Do you want me to log it anyway?"},
                    )
                )
            else:
                actions.append(ActivityDecisionAction(entity="sleep", action="update" if correction_mode else "log", data=data))
            return actions

        quantity_match = re.search(r"(\d+(?:\.\d+)?)\s*(hours|hour|hrs|hr)\b", text)
        if not quantity_match:
            if any(phrase in text for phrase in ["slept badly", "bad sleep", "poor sleep", "sleep was bad", "sleep was awful"]):
                actions.append(ActivityDecisionAction(entity="sleep", action="clarify", data={"question": "How many hours of sleep should I log?"}))
            elif re.search(r"\bsleep\s+\d+(?:\.\d+)?\b", text) or re.search(r"\bslept\s+\d+(?:\.\d+)?\b", text):
                actions.append(
                    ActivityDecisionAction(
                        entity="sleep",
                        action="clarify",
                        data={"question": "Please include hours when logging sleep, for example '7 hours'."},
                    )
                )
            return actions

        hours = float(quantity_match.group(1))
        data = {
            "activity_name": "sleep",
            "value": hours,
            "unit": "hours",
            "duration_minutes": int(hours * 60),
            "logged_for_date": logged_for_date,
            "time_context": time_context,
        }
        if hours > 16:
            actions.append(
                ActivityDecisionAction(
                    entity="sleep",
                    action="confirm",
                    data={**data, "question": f"{hours:g} hours of sleep is unusually high. Do you want me to log it anyway?"},
                )
            )
        else:
            actions.append(ActivityDecisionAction(entity="sleep", action="update" if correction_mode else "log", data=data))
        return actions

    def _extract_weight_actions(
        self,
        text: str,
        logged_for_date: str,
        time_context: str | None,
        correction_mode: bool,
    ) -> list[ActivityDecisionAction]:
        actions: list[ActivityDecisionAction] = []
        mentions_weight = "weight" in text or any(unit in text for unit in self.WEIGHT_UNITS)
        if not mentions_weight:
            return actions

        matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*(kg|kilogram|kilograms|lb|lbs|pound|pounds)\b", text))
        if not matches:
            if "weight" in text:
                actions.append(
                    ActivityDecisionAction(
                        entity="weight",
                        action="clarify",
                        data={"question": "What weight should I log? Please include kg or lb."},
                    )
                )
            return actions

        match = matches[-1] if correction_mode else matches[0]
        value = float(match.group(1))
        unit = self.normalize_unit(match.group(2))
        data = {
            "activity_name": "weight",
            "value": int(round(value)),
            "unit": unit,
            "logged_for_date": logged_for_date,
            "time_context": time_context,
        }
        suspicious = (unit == "kg" and not (20 <= value <= 400)) or (unit == "lb" and not (44 <= value <= 880))
        if suspicious:
            actions.append(
                ActivityDecisionAction(
                    entity="weight",
                    action="confirm",
                    data={**data, "question": f"{value:g} {unit} looks unusual. Do you want me to log it anyway?"},
                )
            )
        else:
            actions.append(ActivityDecisionAction(entity="weight", action="update" if correction_mode else "log", data=data))
        return actions

    def _extract_activity_actions(
        self,
        text: str,
        logged_for_date: str,
        time_context: str | None,
        correction_mode: bool,
    ) -> list[ActivityDecisionAction]:
        actions: list[ActivityDecisionAction] = []
        pattern = re.finditer(
            r"(?:played|did|went\s+for|completed|finished)?\s*(badminton|football|soccer|walking|walk|running|run|jogging|jog|gym|yoga|exercise|workout|training)"
            r"(?:\s+for\s+(\d+(?:\.\d+)?)\s*(minutes|minute|mins|min|hours|hour|hrs|hr))?",
            text,
        )
        for match in pattern:
            raw_name = match.group(1)
            amount = match.group(2)
            raw_unit = match.group(3)
            activity_name = self.normalize_activity_name(raw_name)
            data = {
                "activity_name": activity_name,
                "activity_category": self.infer_category(activity_name),
                "logged_for_date": logged_for_date,
                "time_context": time_context,
            }
            if amount and raw_unit:
                unit = self.normalize_unit(raw_unit)
                numeric_amount = float(amount)
                duration_minutes = int(numeric_amount * 60) if unit == "hours" else int(numeric_amount)
                actions.append(
                    ActivityDecisionAction(
                        entity="activity",
                        action="update" if correction_mode else "log",
                        data={**data, "duration_minutes": duration_minutes},
                    )
                )
            else:
                actions.append(
                    ActivityDecisionAction(
                        entity="activity",
                        action="clarify",
                        data={**data, "question": f"How long did you do {activity_name}?"},
                    )
                )

        if not actions and any(phrase in text for phrase in ["worked out", "exercise", "training"]):
            actions.append(
                ActivityDecisionAction(
                    entity="activity",
                    action="clarify",
                    data={"question": "What activity did you do, and for how long?"},
                )
            )
        return actions

    def _extract_mood_actions(
        self,
        text: str,
        logged_for_date: str,
        time_context: str | None,
        correction_mode: bool,
    ) -> list[ActivityDecisionAction]:
        actions: list[ActivityDecisionAction] = []
        for mood_word in sorted(self.MOOD_WORDS):
            if re.search(rf"\b{re.escape(mood_word)}\b", text):
                actions.append(ActivityDecisionAction(entity="mood", action="retrieve", data={"signal": mood_word}))
                break
        return actions

    def _extract_time_context(self, text: str) -> tuple[str, str | None]:
        logged_for = date.today()
        time_context = None
        if "yesterday" in text:
            logged_for = date.today() - timedelta(days=1)
        elif "two days ago" in text:
            logged_for = date.today() - timedelta(days=2)
        elif "three days ago" in text:
            logged_for = date.today() - timedelta(days=3)
        elif "last night" in text:
            logged_for = date.today() - timedelta(days=1)
            time_context = "night"
        elif "last evening" in text:
            logged_for = date.today() - timedelta(days=1)
            time_context = "evening"
        elif "last afternoon" in text:
            logged_for = date.today() - timedelta(days=1)
            time_context = "afternoon"
        elif "last morning" in text:
            logged_for = date.today() - timedelta(days=1)
            time_context = "morning"
        elif "last week" in text:
            logged_for = date.today() - timedelta(days=7)
        elif "today" in text:
            logged_for = date.today()

        for label in ["this morning", "morning", "this afternoon", "afternoon", "this evening", "evening", "tonight", "night"]:
            if label in text and time_context is None:
                time_context = label
                break
        return logged_for.isoformat(), time_context

    def _is_correction(self, text: str) -> bool:
        correction_phrases = ["no actually", "actually", "correction", "instead", "make that", "sorry", "not "]
        return any(phrase in text for phrase in correction_phrases)

    def _convert_water_to_ml(self, value: float, unit: str | None) -> int:
        multiplier = {
            "ml": 1,
            "glasses": 250,
            "cups": 240,
            "bottles": 500,
            "liters": 1000,
        }.get(unit or "")
        if multiplier is None:
            return int(round(value))
        return int(round(value * multiplier))

    def _normalize_text(self, message: str) -> str:
        return re.sub(r"\s+", " ", message.strip().lower())

    def _normalize_time_context_label(self, label: str | None) -> str | None:
        if not label:
            return None
        normalized = str(label).strip().lower()
        mapping = {
            "last night": "night",
            "last evening": "evening",
            "last afternoon": "afternoon",
            "last morning": "morning",
        }
        return mapping.get(normalized, normalized)

    def _dedupe_actions(self, actions: list[ActivityDecisionAction]) -> list[ActivityDecisionAction]:
        deduped: list[ActivityDecisionAction] = []
        seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
        for action in actions:
            key = (
                action.entity,
                action.action,
                tuple(sorted((str(k), repr(v)) for k, v in action.data.items())),
            )
            if key not in seen:
                seen.add(key)
                deduped.append(action)
        return deduped

    def _build_summary(self, actions: list[ActivityDecisionAction]) -> str:
        if all(action.action == "none" for action in actions):
            return "No structured activity action detected."
        return "Detected actions -> " + ", ".join(f"{action.entity}:{action.action}" for action in actions)

    def _apply_single_action(self, db, user_id: int, action: ActivityDecisionAction) -> dict:
        logged_day = self._parse_logged_day(action.data.get("logged_for_date"))
        occurred_at = self._build_occurred_at(logged_day, action.data.get("time_context"))

        if action.entity == "water":
            return self._apply_water_action(db=db, user_id=user_id, action=action, logged_day=logged_day, occurred_at=occurred_at)
        if action.entity == "sleep":
            return self._apply_sleep_action(db=db, user_id=user_id, action=action, logged_day=logged_day, occurred_at=occurred_at)
        if action.entity == "weight":
            return self._apply_weight_action(db=db, user_id=user_id, action=action, logged_day=logged_day, occurred_at=occurred_at)
        if action.entity == "activity":
            return self._apply_generic_activity_action(db=db, user_id=user_id, action=action, logged_day=logged_day, occurred_at=occurred_at)
        return {"entity": action.entity, "status": "skipped", "reason": "unsupported_entity"}

    def _apply_water_action(self, db, user_id: int, action: ActivityDecisionAction, logged_day: date, occurred_at: datetime) -> dict:
        amount_ml = int(round(action.data.get("value") or 0))
        existing = self.get_latest_activity_for_day(db=db, user_id=user_id, activity_name="water", day=logged_day)
        total_today = self.get_total_value_for_day(db=db, user_id=user_id, activity_name="water", day=logged_day)

        if action.action == "update":
            new_total = amount_ml
            note_prefix = "Corrected cumulative water total."
        else:
            new_total = total_today + amount_ml
            note_prefix = "Cumulative daily water total."

        notes = self._merge_notes(
            note_prefix,
            action.data.get("notes"),
            f"Latest added: {action.data.get('display_value', amount_ml):g} {action.data.get('display_unit', 'ml')}",
        )
        if existing and existing.unit == "ml":
            updated = self.update_activity_log(
                db=db,
                activity_log=existing,
                value=new_total,
                unit="ml",
                notes=notes,
            )
            challenge_result = self.challenge_service.record_water_event(db=db, user_id=user_id, value=amount_ml, message=notes)
            return {"entity": "water", "status": "updated", "record_id": updated.id, "value": updated.value, "unit": updated.unit, "celebration": challenge_result.get("celebration") if isinstance(challenge_result, dict) else None}

        created = self.log_activity(
            db=db,
            user_id=user_id,
            activity_name="water",
            value=new_total,
            unit="ml",
            notes=notes,
            created_at=occurred_at,
        )
        challenge_result = getattr(created, "challenge_result", None)
        return {"entity": "water", "status": "logged", "record_id": created.id, "value": created.value, "unit": created.unit, "celebration": challenge_result.get("celebration") if isinstance(challenge_result, dict) else None}

    def _apply_sleep_action(self, db, user_id: int, action: ActivityDecisionAction, logged_day: date, occurred_at: datetime) -> dict:
        existing = self.get_latest_activity_for_day(db=db, user_id=user_id, activity_name="sleep", day=logged_day)
        notes = self._merge_notes("Daily sleep record.", action.data.get("notes"))
        if existing:
            updated = self.update_activity_log(
                db=db,
                activity_log=existing,
                value=action.data.get("value"),
                unit=action.data.get("unit", "hours"),
                duration_minutes=action.data.get("duration_minutes"),
                notes=notes,
            )
            challenge_result = self.challenge_service.record_sleep_event(
                db=db,
                user_id=user_id,
                duration_minutes=action.data.get("duration_minutes"),
                message=notes,
            )
            return {"entity": "sleep", "status": "updated", "record_id": updated.id, "value": updated.value, "unit": updated.unit, "celebration": challenge_result.get("celebration") if isinstance(challenge_result, dict) else None}

        created = self.log_activity(
            db=db,
            user_id=user_id,
            activity_name="sleep",
            value=action.data.get("value"),
            unit=action.data.get("unit", "hours"),
            duration_minutes=action.data.get("duration_minutes"),
            notes=notes,
            created_at=occurred_at,
        )
        challenge_result = getattr(created, "challenge_result", None)
        return {"entity": "sleep", "status": "logged", "record_id": created.id, "value": created.value, "unit": created.unit, "celebration": challenge_result.get("celebration") if isinstance(challenge_result, dict) else None}

    def _apply_weight_action(self, db, user_id: int, action: ActivityDecisionAction, logged_day: date, occurred_at: datetime) -> dict:
        existing = self.get_latest_activity_for_day(db=db, user_id=user_id, activity_name="weight", day=logged_day)
        notes = self._merge_notes("Latest daily weight record.", action.data.get("notes"))
        if existing:
            updated = self.update_activity_log(
                db=db,
                activity_log=existing,
                value=action.data.get("value"),
                unit=action.data.get("unit", "kg"),
                notes=notes,
            )
            return {"entity": "weight", "status": "updated", "record_id": updated.id, "value": updated.value, "unit": updated.unit}

        created = self.log_activity(
            db=db,
            user_id=user_id,
            activity_name="weight",
            value=action.data.get("value"),
            unit=action.data.get("unit", "kg"),
            notes=notes,
            created_at=occurred_at,
        )
        return {"entity": "weight", "status": "logged", "record_id": created.id, "value": created.value, "unit": created.unit}

    def _apply_generic_activity_action(self, db, user_id: int, action: ActivityDecisionAction, logged_day: date, occurred_at: datetime) -> dict:
        activity_name = action.data.get("activity_name", "activity")
        existing = self.get_latest_activity_for_day(db=db, user_id=user_id, activity_name=activity_name, day=logged_day)
        should_update = action.action == "update" and existing is not None
        if should_update:
            updated = self.update_activity_log(
                db=db,
                activity_log=existing,
                value=action.data.get("value"),
                unit=action.data.get("unit"),
                duration_minutes=action.data.get("duration_minutes"),
                notes=self._merge_notes("Updated activity record.", action.data.get("notes")),
            )
            challenge_result = self.challenge_service.record_activity_event(
                db=db,
                user_id=user_id,
                activity_name=activity_name,
                duration_minutes=action.data.get("duration_minutes"),
                message=action.data.get("notes"),
            )
            return {
                "entity": "activity",
                "status": "updated",
                "record_id": updated.id,
                "activity_name": updated.activity_name,
                "duration_minutes": updated.duration_minutes,
                "value": updated.value,
                "unit": updated.unit,
                "celebration": challenge_result.get("celebration") if isinstance(challenge_result, dict) else None,
            }

        created = self.log_activity(
            db=db,
            user_id=user_id,
            activity_name=activity_name,
            value=action.data.get("value"),
            unit=action.data.get("unit"),
            duration_minutes=action.data.get("duration_minutes"),
            notes=self._merge_notes("Logged activity record.", action.data.get("notes")),
            created_at=occurred_at,
        )
        challenge_result = getattr(created, "challenge_result", None)
        return {
            "entity": "activity",
            "status": "logged",
            "record_id": created.id,
            "activity_name": created.activity_name,
            "duration_minutes": created.duration_minutes,
            "value": created.value,
            "unit": created.unit,
            "celebration": challenge_result.get("celebration") if isinstance(challenge_result, dict) else None,
        }

    def _parse_logged_day(self, raw_day: str | None) -> date:
        if not raw_day:
            return date.today()
        return date.fromisoformat(raw_day)

    def _build_occurred_at(self, logged_day: date, time_context: str | None) -> datetime:
        time_map = {
            "this morning": time(9, 0),
            "morning": time(9, 0),
            "this afternoon": time(14, 0),
            "afternoon": time(14, 0),
            "this evening": time(19, 0),
            "evening": time(19, 0),
            "tonight": time(22, 0),
            "night": time(22, 0),
        }
        return datetime.combine(logged_day, time_map.get(time_context, time(12, 0)))

    def _merge_notes(self, *parts: str | None) -> str | None:
        cleaned = [part.strip() for part in parts if part and str(part).strip()]
        if not cleaned:
            return None
        return " ".join(cleaned)

    def extract_sleep_hours_from_text(self, message: str) -> float | None:
        text = self._normalize_text(message)
        match = re.search(r"(\d+(?:\.\d+)?)\s*(hours|hour|hrs|hr)?\b", text)
        if not match:
            return None
        value = float(match.group(1))
        if 0 < value <= 24:
            return value
        return None

    def extract_duration_minutes_from_text(self, message: str) -> int | None:
        text = self._normalize_text(message)
        match = re.search(r"(\d+(?:\.\d+)?)\s*(minutes|minute|mins|min|hours|hour|hrs|hr)\b", text)
        if not match:
            return None
        value = float(match.group(1))
        unit = self.normalize_unit(match.group(2))
        if unit == "hours":
            return int(value * 60)
        return int(value)

    def log_activity(
        self,
        db,
        user_id: int,
        activity_name: str,
        value: int | None = None,
        unit: str | None = None,
        duration_minutes: int | None = None,
        notes: str | None = None,
        created_at: datetime | None = None,
    ):
        activity_input = ActivityLogInput(
            activity_name=activity_name,
            value=value,
            unit=unit,
            duration_minutes=duration_minutes,
            notes=notes,
        )
        normalized_name = self.normalize_activity_name(activity_input.activity_name)
        normalized_unit = self.normalize_unit(activity_input.unit)
        category = self.infer_category(normalized_name)
        
        # Calculate fitness metrics for exercise activities
        fitness_metrics = None
        calories_burned = None
        steps_count = None
        intensity_level = None
        
        if category == "exercise" and duration_minutes:
            profile = self.profile_repository.get_profile(db=db, user_id=user_id)
            user_weight = profile.weight_kg if profile and profile.weight_kg else 70.0
            user_age = profile.age if profile and profile.age else 30
            user_gender = profile.gender if profile and profile.gender else "male"
            
            fitness_metrics = fitness_calculator.calculate_metrics(
                activity_name=normalized_name,
                duration_minutes=duration_minutes,
                user_weight_kg=user_weight,
                user_age=user_age,
                user_gender=user_gender
            )
            
            # Store in dedicated columns
            calories_burned = int(round(fitness_metrics.calories))
            steps_count = fitness_metrics.steps
            intensity_level = fitness_metrics.intensity
        
        activity_log = self.activity_repository.create_activity_log(
            db=db,
            user_id=user_id,
            activity_category=category,
            activity_name=normalized_name,
            value=int(round(activity_input.value)) if activity_input.value is not None else None,
            unit=normalized_unit,
            duration_minutes=activity_input.duration_minutes,
            notes=notes,
            calories_burned=calories_burned,
            steps_count=steps_count,
            intensity_level=intensity_level,
            created_at=created_at,
        )
        
        if normalized_name == "water":
            challenge_result = self.challenge_service.record_water_event(db=db, user_id=user_id, value=activity_input.value, message=activity_input.notes)
        elif normalized_name == "sleep":
            challenge_result = self.challenge_service.record_sleep_event(
                db=db,
                user_id=user_id,
                duration_minutes=activity_input.duration_minutes,
                message=activity_input.notes,
            )
        elif category == "exercise":
            challenge_result = self.challenge_service.record_activity_event(
                db=db,
                user_id=user_id,
                activity_name=normalized_name,
                duration_minutes=activity_input.duration_minutes,
                message=activity_input.notes,
            )
        else:
            challenge_result = None
        
        setattr(activity_log, "challenge_result", challenge_result)
        setattr(activity_log, "fitness_metrics", fitness_metrics)
        return activity_log

    def update_activity_log(self, db, activity_log, **kwargs):
        if "value" in kwargs and kwargs["value"] is not None:
            kwargs["value"] = int(round(kwargs["value"]))
        if "unit" in kwargs:
            kwargs["unit"] = self.normalize_unit(kwargs["unit"])
        return self.activity_repository.update_activity_log(db=db, activity_log=activity_log, **kwargs)

    def get_recent_activities(self, db, user_id: int, limit: int = 5):
        return self.activity_repository.get_recent_activities(db=db, user_id=user_id, limit=limit)

    def get_latest_activity_for_day(self, db, user_id: int, activity_name: str, day: date | None = None):
        normalized_name = self.normalize_activity_name(activity_name)
        return self.activity_repository.get_latest_activity_for_day(db=db, user_id=user_id, activity_name=normalized_name, day=day)

    def get_total_value_for_day(self, db, user_id: int, activity_name: str, day: date | None = None) -> int:
        normalized_name = self.normalize_activity_name(activity_name)
        return self.activity_repository.get_total_value_for_day(db=db, user_id=user_id, activity_name=normalized_name, day=day)

    def get_daily_fitness_metrics(self, db, user_id: int, day: date | None = None) -> dict:
        """
        Extract and aggregate fitness metrics (steps, calories) from today's exercise activities.
        """
        day = day or date.today()
        activities = self.activity_repository.list_activities_for_day(db=db, user_id=user_id, day=day)
        
        total_steps = 0
        total_calories = 0.0
        exercise_count = 0
        intensity_counts = {"low": 0, "moderate": 0, "high": 0, "very_high": 0}
        
        for activity in activities:
            if activity.activity_category == "exercise":
                # Use stored fitness metrics from database
                if activity.steps_count:
                    total_steps += activity.steps_count
                if activity.calories_burned:
                    total_calories += activity.calories_burned
                if activity.intensity_level:
                    intensity_counts[activity.intensity_level] = intensity_counts.get(activity.intensity_level, 0) + 1
                
                if activity.steps_count or activity.calories_burned:
                    exercise_count += 1
        
        # Determine overall intensity
        if intensity_counts["very_high"] > 0:
            overall_intensity = "very_high"
        elif intensity_counts["high"] > 0:
            overall_intensity = "high"
        elif intensity_counts["moderate"] > 0:
            overall_intensity = "moderate"
        else:
            overall_intensity = "low"
        
        return {
            "date": day.isoformat(),
            "total_steps": total_steps,
            "total_calories": round(total_calories, 1),
            "exercise_count": exercise_count,
            "overall_intensity": overall_intensity,
            "intensity_breakdown": intensity_counts
        }
    
    def get_fitness_summary(self, db, user_id: int, activity_log) -> str:
        """Generate formatted fitness summary for chat display"""
        if not activity_log.calories_burned and not activity_log.steps_count:
            return ""
        
        parts = []
        if activity_log.calories_burned:
            parts.append(f"🔥 {activity_log.calories_burned} calories burned")
        if activity_log.steps_count:
            parts.append(f"👟 {activity_log.steps_count:,} steps")
        if activity_log.intensity_level:
            intensity_emoji = {
                "low": "🟢",
                "moderate": "🟡", 
                "high": "🟠",
                "very_high": "🔴"
            }.get(activity_log.intensity_level, "⚪")
            parts.append(f"{intensity_emoji} {activity_log.intensity_level.replace('_', ' ').title()} intensity")
        
        return " | ".join(parts)
    
    def get_wellness_suggestions(self, db, user_id: int, activity_log) -> list[str]:
        """Generate proactive wellness suggestions based on activity"""
        if activity_log.activity_category != "exercise":
            return []
        
        profile = self.profile_repository.get_profile(db=db, user_id=user_id)
        user_weight = profile.weight_kg if profile and profile.weight_kg else 70.0
        user_age = profile.age if profile and profile.age else 30
        user_gender = profile.gender if profile and profile.gender else "male"
        
        # Recalculate to get recommendations
        fitness_metrics = fitness_calculator.calculate_metrics(
            activity_name=activity_log.activity_name,
            duration_minutes=activity_log.duration_minutes or 0,
            user_weight_kg=user_weight,
            user_age=user_age,
            user_gender=user_gender
        )
        
        recommendations = fitness_calculator.get_recommendation(fitness_metrics)
        
        suggestions = []
        if recommendations.get("hydration"):
            suggestions.append(recommendations["hydration"])
        if recommendations.get("recovery"):
            suggestions.append(recommendations["recovery"])
        if recommendations.get("nutrition"):
            suggestions.append(recommendations["nutrition"])
        
        return suggestions
