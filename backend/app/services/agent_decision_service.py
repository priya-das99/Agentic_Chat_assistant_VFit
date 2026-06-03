"""
Agent Decision Service - Determines WHEN the agent should intervene

This is the core of proactive agentic behavior. The agent analyzes user state
and autonomously decides if intervention is needed.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from dataclasses import dataclass

from app.repositories.mood_repository import MoodRepository
from app.repositories.activity_repository import ActivityRepository


@dataclass
class InterventionDecision:
    """Decision about whether agent should intervene"""
    should_intervene: bool
    intervention_type: str  # mental_health_check, gentle_nudge, celebrate, weekly_support
    reason: str
    priority: int  # 1=urgent, 2=important, 3=nice-to-have
    suggested_message: str
    timing: str  # now, evening, morning


class AgentDecisionService:
    """
    AGENTIC DECISION MAKING: Determines when agent should proactively reach out
    
    This is what makes the system truly agentic - it observes user patterns
    and decides to act without being asked.
    """
    
    def __init__(self):
        self.mood_repo = MoodRepository()
        self.activity_repo = ActivityRepository()
    
    def should_intervene(
        self, 
        db: Session, 
        user_id: int,
        check_last_intervention: bool = True
    ) -> InterventionDecision:
        """
        Main decision function - analyzes user state and decides if intervention needed
        
        Priority order:
        1. Mental health (declining mood) - URGENT
        2. Inactivity (no engagement) - IMPORTANT
        3. Celebration (positive streak) - NICE-TO-HAVE
        4. Weekly support (low exercise) - NICE-TO-HAVE
        """
        
        # Get user data
        recent_moods = self.mood_repo.get_recent_moods(db, user_id, limit=5)
        recent_activities = self.activity_repo.get_recent_activities(db, user_id, limit=1)
        last_activity = recent_activities[0] if recent_activities else None
        
        # Check if we intervened recently (avoid spam)
        if check_last_intervention:
            if self._intervened_recently(db, user_id, hours=24):
                return InterventionDecision(
                    should_intervene=False,
                    intervention_type="none",
                    reason="Intervened within last 24 hours",
                    priority=0,
                    suggested_message="",
                    timing="later"
                )
        
        # Priority 1: Declining mood pattern (URGENT)
        if self._has_declining_mood_pattern(recent_moods):
            return InterventionDecision(
                should_intervene=True,
                intervention_type="mental_health_check",
                reason="User has 3+ consecutive low moods",
                priority=1,
                suggested_message="I've noticed you've been feeling down lately. Want to talk about it?",
                timing="now"
            )
        
        # Priority 2: Prolonged inactivity (IMPORTANT)
        if self._is_inactive(last_activity, days=3):
            return InterventionDecision(
                should_intervene=True,
                intervention_type="gentle_nudge",
                reason="User hasn't logged anything in 3 days",
                priority=2,
                suggested_message="Hey! It's been a few days. How are you doing?",
                timing="now"
            )
        
        # Priority 3: Positive streak (CELEBRATION)
        if self._has_positive_streak(recent_moods, days=5):
            return InterventionDecision(
                should_intervene=True,
                intervention_type="celebrate",
                reason="User has 5+ consecutive positive moods",
                priority=3,
                suggested_message="You've had 5 positive days in a row! That's amazing! 🎉 Keep it up!",
                timing="now"
            )
        
        # Priority 4: Low weekly activity on Friday (SUPPORT)
        if datetime.now().weekday() == 4:  # Friday
            weekly_exercise = self._get_weekly_exercise_minutes(db, user_id)
            if weekly_exercise < 60:
                return InterventionDecision(
                    should_intervene=True,
                    intervention_type="weekly_support",
                    reason="Low exercise this week, Friday check-in",
                    priority=3,
                    suggested_message=f"You've logged {weekly_exercise} exercise minutes this week. Want to squeeze in a quick workout this weekend?",
                    timing="evening"
                )
        
        # No intervention needed
        return InterventionDecision(
            should_intervene=False,
            intervention_type="none",
            reason="User state is healthy",
            priority=0,
            suggested_message="",
            timing="later"
        )
    
    def _has_declining_mood_pattern(self, recent_moods: list) -> bool:
        """Check if user has declining mood pattern (3+ consecutive low moods)"""
        if len(recent_moods) < 3:
            return False
        
        # Check last 3 moods
        last_3 = recent_moods[:3]
        low_moods = ["sad", "stressed", "anxious", "angry", "tired"]
        
        low_mood_count = sum(1 for mood in last_3 if mood.mood_label.lower() in low_moods)
        return low_mood_count >= 3
    
    def _is_inactive(self, last_activity, days: int) -> bool:
        """Check if user has been inactive for N days"""
        if not last_activity:
            return True
        
        inactive_threshold = datetime.now() - timedelta(days=days)
        return last_activity.created_at < inactive_threshold
    
    def _has_positive_streak(self, recent_moods: list, days: int) -> bool:
        """Check if user has positive mood streak"""
        if len(recent_moods) < days:
            return False
        
        positive_moods = ["great", "happy", "good"]
        positive_count = sum(
            1 for mood in recent_moods[:days] 
            if mood.mood_label.lower() in positive_moods
        )
        
        return positive_count >= days
    
    def _get_weekly_exercise_minutes(self, db: Session, user_id: int) -> int:
        """Get total exercise minutes this week"""
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        activities = self.activity_repo.list_activities_between(
            db=db,
            user_id=user_id,
            start_day=week_start.date(),
            end_day=datetime.now().date()
        )
        
        return sum(
            int(activity.duration_minutes or 0) 
            for activity in activities 
            if activity.activity_category == "exercise"
        )
    
    def _intervened_recently(self, db: Session, user_id: int, hours: int = 24) -> bool:
        """
        Check if we intervened recently
        
        For now, we check chat history for proactive messages.
        In future, create intervention_log table for better tracking.
        """
        from app.repositories.chat_repository import ChatRepository
        
        chat_repo = ChatRepository()
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # Get recent assistant messages
        recent_messages = chat_repo.get_recent_messages(db, user_id, limit=10)
        
        for msg in recent_messages:
            if msg.created_at < cutoff:
                break
            
            # Check if message is from assistant (proactive messages are from assistant)
            # and contains proactive keywords
            if msg.role == "assistant":
                # Simple heuristic: if message starts with certain phrases, it's likely proactive
                proactive_phrases = [
                    "I've noticed",
                    "It's been a few days",
                    "You've had",
                    "Hey! ",
                    "How are you doing"
                ]
                
                if any(msg.message.startswith(phrase) for phrase in proactive_phrases):
                    return True
        
        return False
