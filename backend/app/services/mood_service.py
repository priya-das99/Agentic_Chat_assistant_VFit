import re

from app.models.api_models import MoodLogInput, MoodParseResult
from app.repositories.mood_repository import MoodRepository
from app.services.challenge_service import ChallengeService


class MoodService:
    QUICK_MOOD_OPTIONS = [
        {"label": "Ok", "mood_label": "neutral", "emoji": "😐", "requires_reason": False},
        {"label": "Not good", "mood_label": "sad", "emoji": "😕", "requires_reason": True},
        {"label": "Pretty Good", "mood_label": "happy", "emoji": "🙂", "requires_reason": False},
        {"label": "Awesome", "mood_label": "great", "emoji": "😄", "requires_reason": False},
        {"label": "Horrible", "mood_label": "sad", "emoji": "😣", "requires_reason": True},
    ]

    QUICK_MOOD_ALIAS_MAP = {
        "ok": "neutral",
        "okay": "neutral",
        "not good": "sad",
        "pretty good": "happy",
        "awesome": "great",
        "horrible": "sad",
        "bad": "sad",
        "awful": "sad",
        "terrible": "sad",
        "upset": "sad",
        "depressed": "sad",
        "good": "happy",
        "amazing": "great",
        "fantastic": "great",
        "wonderful": "great",
        "fine": "neutral",
        "so so": "neutral",
        "meh": "neutral",
        "relaxed": "calm",
        "peaceful": "calm",
        "great": "great",
        "happy": "happy",
        "calm": "calm",
        "neutral": "neutral",
        "tired": "tired",
        "stressed": "stressed",
        "sad": "sad",
        "anxious": "anxious",
    }

    MOOD_SCORE_MAP = {
        "great": 5,
        "happy": 4,
        "calm": 4,
        "neutral": 3,
        "tired": 2,
        "stressed": 2,
        "sad": 1,
        "anxious": 1,
    }

    def __init__(self):
        self.mood_repository = MoodRepository()
        self.challenge_service = ChallengeService()

    def normalize_mood(self, mood_label: str) -> tuple[str, int | None]:
        normalized = mood_label.strip().lower()
        normalized = self.QUICK_MOOD_ALIAS_MAP.get(normalized, normalized)
        score = self.MOOD_SCORE_MAP.get(normalized)
        return normalized, score

    def get_quick_mood_options(self) -> list[dict]:
        return list(self.QUICK_MOOD_OPTIONS)

    def get_reason_options_for_mood(self, mood_label: str) -> list[dict]:
        normalized, score = self.normalize_mood(mood_label)
        if score is not None and score > 2:
            return []

        return [
            {"label": "Work pressure", "mood_label": normalized, "emoji": "💼", "requires_reason": False},
            {"label": "Poor sleep", "mood_label": normalized, "emoji": "😴", "requires_reason": False},
            {"label": "Health issue", "mood_label": normalized, "emoji": "🤒", "requires_reason": False},
            {"label": "Family or relationship", "mood_label": normalized, "emoji": "👨‍👩‍👧‍👦", "requires_reason": False},
            {"label": "Food", "mood_label": normalized, "emoji": "🍽️", "requires_reason": False},
            {"label": "Travel", "mood_label": normalized, "emoji": "✈️", "requires_reason": False},
            {"label": "Friend", "mood_label": normalized, "emoji": "👥", "requires_reason": False},
            {"label": "Other", "mood_label": normalized, "emoji": "✍️", "requires_reason": True},
        ]

    def build_motivational_reply(self, mood_label: str, reason: str | None = None) -> str:
        normalized, _ = self.normalize_mood(mood_label)
        if normalized in {"great", "happy"}:
            return "Nice, that’s a strong mood. Keep going and carry this momentum into the rest of your day."
        if normalized == "calm":
            return "That sounds steady and balanced. A calm day is a good foundation."
        if normalized == "neutral":
            return "Logged. A steady day still counts, and it gives us a clear baseline."
        if normalized in {"tired", "stressed", "sad", "anxious"}:
            base = "Logged, and thank you for sharing that."
            if reason:
                return f"{base} We’ll keep an eye on it and use that context to support you better."
            return f"{base} If you want, add a quick reason so I can tailor the support a bit more."
        return "Mood logged."

    def needs_reason_for_mood(self, mood_label: str) -> bool:
        normalized, score = self.normalize_mood(mood_label)
        if normalized in {"sad", "stressed", "anxious"}:
            return True
        return score is not None and score <= 2

    def is_mood_query(self, message: str) -> bool:
        """
        Check if the message is asking about mood rather than expressing it.
        Returns True for questions like "How am I feeling?" or "What's my mood?"
        """
        text = message.strip().lower()
        
        query_indicators = [
            r'\bhow\s+(have\s+i|am\s+i|do\s+i|did\s+i)',
            r'\bwhat\s+(is|was|are|were)',
            r'\bwhy\s+',
            r'\bshow\s+(me\s+)?my',
            r'\bcan\s+you\s+(show|tell)',
            r'\btell\s+me\s+about',
            r'\?$',  # Ends with question mark
        ]
        
        return any(re.search(pattern, text) for pattern in query_indicators)

    def parse_mood_text(self, message: str, require_explicit_intent: bool = False) -> MoodParseResult:
        """
        Parse mood from text message.
        
        Args:
            message: The user's message
            require_explicit_intent: If True, only match explicit logging requests like
                                    "log my mood as X" or "I want to log X"
        """
        text = message.strip().lower()
        
        # Check for question patterns - these should NOT trigger mood logging
        question_patterns = [
            r'\bhow\s+(have\s+i|am\s+i|do\s+i)',  # "how have I been feeling"
            r'\bwhat\s+',  # "what affects my mood"
            r'\bwhy\s+',   # "why do I feel"
            r'\bshow\s+',  # "show me my mood"
            r'\bcan\s+you', # "can you show"
            r'\?',         # Any question mark
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, text):
                return MoodParseResult(matched=False)
        
        # If require_explicit_intent, only match explicit logging requests
        if require_explicit_intent:
            explicit_pattern = re.search(
                r"(?:log|record|track|save)\s+(?:my\s+)?mood\s+(?:as\s+)?(\w+)",
                text,
            )
            if not explicit_pattern:
                return MoodParseResult(matched=False)
        
        ordered_mood_phrases = sorted(self.QUICK_MOOD_ALIAS_MAP.keys(), key=len, reverse=True)

        # Check for negation patterns first (e.g., "not feeling good", "not okay")
        negation_pattern = re.search(
            r"(?:not|never|no)\s+(?:feeling\s+)?("
            + "|".join(re.escape(mood) for mood in ordered_mood_phrases)
            + r")(?:\s+because\s+(.+))?",
            text,
        )
        if negation_pattern:
            # If they say "not good", "not okay", etc., interpret as sad/negative
            negated_mood = negation_pattern.group(1)
            reason = negation_pattern.group(2).strip() if negation_pattern.group(2) else None
            
            # Map negated positive moods to negative moods
            if negated_mood in ["good", "okay", "ok", "fine", "great", "happy", "amazing", "fantastic", "wonderful", "pretty good"]:
                normalized_mood = "sad"
            else:
                # If they negate a negative mood (e.g., "not sad"), treat as neutral
                normalized_mood = "neutral"
            
            mood_score = self.MOOD_SCORE_MAP.get(normalized_mood)
            return MoodParseResult(
                matched=True,
                mood_label=normalized_mood,
                mood_score=mood_score,
                reason=reason,
            )

        # Standard mood pattern (without negation)
        mood_pattern = re.search(
            r"(?:i feel|i am feeling|i'm feeling|feeling|log my mood as|my mood is|i am|i'm)\s+("
            + "|".join(re.escape(mood) for mood in ordered_mood_phrases)
            + r")(?:\s+because\s+(.+))?",
            text,
        )
        if mood_pattern:
            mood_label = mood_pattern.group(1)
            reason = mood_pattern.group(2).strip() if mood_pattern.group(2) else None
            normalized_mood, mood_score = self.normalize_mood(mood_label)
            return MoodParseResult(
                matched=True,
                mood_label=normalized_mood,
                mood_score=mood_score,
                reason=reason,
            )

        standalone_pattern = re.search(
            r"\b("
            + "|".join(re.escape(mood) for mood in ordered_mood_phrases)
            + r")\b",
            text,
        )
        if standalone_pattern:
            mood_label = standalone_pattern.group(1)
            normalized_mood, mood_score = self.normalize_mood(mood_label)
            return MoodParseResult(
                matched=True,
                mood_label=normalized_mood,
                mood_score=mood_score,
            )

        return MoodParseResult(matched=False)

    def log_mood(self, db, user_id: int, mood_label: str, reason: str | None = None):
        mood_input = MoodLogInput(mood_label=mood_label, reason=reason)
        normalized_mood, mood_score = self.normalize_mood(mood_input.mood_label)
        mood_log = self.mood_repository.create_mood_log(
            db=db,
            user_id=user_id,
            mood_label=normalized_mood,
            mood_score=mood_score,
            reason=mood_input.reason,
        )
        challenge_result = self.challenge_service.record_mood_event(db=db, user_id=user_id, message=mood_input.reason or normalized_mood)
        return mood_log, challenge_result

    def log_quick_mood(self, db, user_id: int, mood_label: str, reason: str | None = None) -> dict:
        normalized_mood, mood_score = self.normalize_mood(mood_label)
        if self.needs_reason_for_mood(normalized_mood) and not reason:
            return {
                "success": False,
                "needs_reason": True,
                "mood_label": normalized_mood,
                "mood_score": mood_score,
                "emoji": self.get_mood_emoji(normalized_mood),
                "message": "Please choose a reason so I can log this mood with a bit more context.",
                "reason_options": self.get_reason_options_for_mood(normalized_mood),
                "available_options": self.get_quick_mood_options(),
            }

        mood_log, challenge_result = self.log_mood(db=db, user_id=user_id, mood_label=normalized_mood, reason=reason)
        celebration = challenge_result.get("celebration") if isinstance(challenge_result, dict) else None
        message = self.build_motivational_reply(mood_log.mood_label, mood_log.reason)
        if celebration:
            message = f"{message} {celebration}"
        return {
            "success": True,
            "needs_reason": False,
            "mood_label": mood_log.mood_label,
            "mood_score": mood_log.mood_score,
            "emoji": self.get_mood_emoji(mood_log.mood_label),
            "reason": mood_log.reason,
            "message": message,
            "available_options": self.get_quick_mood_options(),
            "reason_options": self.get_reason_options_for_mood(mood_log.mood_label),
            "challenge_result": challenge_result,
        }

    def get_mood_emoji(self, mood_label: str) -> str:
        normalized, _ = self.normalize_mood(mood_label)
        emoji_map = {
            "great": "😄",
            "happy": "🙂",
            "calm": "😌",
            "neutral": "😐",
            "tired": "😴",
            "stressed": "😣",
            "sad": "😕",
            "anxious": "😟",
        }
        return emoji_map.get(normalized, "🙂")

    def get_recent_moods(self, db, user_id: int, limit: int = 5):
        return self.mood_repository.get_recent_moods(db=db, user_id=user_id, limit=limit)
