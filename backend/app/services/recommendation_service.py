"""
Recommendation Service - Smart content suggestions based on user context and history
"""

from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
import json

from app.repositories.content_library_repository import ContentLibraryRepository
from app.repositories.mood_repository import MoodRepository
from app.repositories.activity_repository import ActivityRepository


class RecommendationService:
    """
    Smart content recommendations based on:
    - Current context (mood, energy, time)
    - User history (what they've engaged with)
    - Personalization (what works for them)
    """
    
    def __init__(self):
        self.content_repo = ContentLibraryRepository()
        self.mood_repo = MoodRepository()
        self.activity_repo = ActivityRepository()
    
    def get_personalized_content(
        self,
        db: Session,
        user_id: int,
        context: Dict = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        Get personalized content suggestions that adapt to user behavior
        
        Args:
            db: Database session
            user_id: User ID
            context: Optional context dict with:
                - mood: current mood (stressed, happy, tired, etc.)
                - energy_level: low, medium, high
                - time_available: minutes
                - time_of_day: morning, afternoon, evening
                - category: specific category to filter
                - content_type: video, article, audio, guide
                - week_progress: start, mid, end (for weekly adaptation)
                - exercise_done_today: boolean
                - exercise_minutes_week: total minutes this week
                - sleep_quality: good, poor, none (tracked this week)
            limit: Number of suggestions to return
        
        Returns:
            List of content dicts with title, url, description, score, reason
        """
        context = context or {}
        
        # Get all active content
        all_content = self.content_repo.list_all_active(db)
        
        if not all_content:
            return []
        
        # Get user history for personalization and tracking
        recent_moods = self.mood_repo.get_recent_moods(db, user_id, limit=7)
        user_interactions = self.content_repo.get_user_history(db, user_id, limit=20)
        
        # Get user activity data for the week
        week_activities = self._get_week_activity_summary(db, user_id)
        
        # Enhance context with activity tracking
        context = self._enhance_context_with_activity(context, week_activities)
        
        # Score each content item
        scored_content = []
        for content in all_content:
            score = self._score_content(
                content=content,
                context=context,
                recent_moods=recent_moods,
                user_interactions=user_interactions,
                week_activities=week_activities
            )
            
            if score > 0:
                scored_content.append({
                    "id": content.id,
                    "title": content.title,
                    "description": content.description,
                    "content_type": content.content_type,
                    "url": content.url,
                    "thumbnail_url": content.thumbnail_url,
                    "category_label": content.category_label,
                    "duration_minutes": content.duration_minutes,
                    "difficulty": content.difficulty,
                    "score": round(score, 1),
                    "reason": self._generate_reason(content, context, user_interactions, week_activities)
                })
        
        # Sort by score
        scored_content.sort(key=lambda x: x["score"], reverse=True)
        
        # Ensure diverse categories: don't return all from same category
        # Use round-robin selection to maximize diversity
        diverse_results = []
        category_groups = {}
        
        # Group by category
        for item in scored_content:
            category = item.get("category_label", "Other")
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(item)
        
        # Round-robin selection: take one from each category until we reach limit
        category_lists = list(category_groups.values())
        category_index = 0
        
        while len(diverse_results) < limit and any(category_lists):
            # Get next category in round-robin
            current_list = category_lists[category_index % len(category_lists)]
            
            if current_list:
                diverse_results.append(current_list.pop(0))
            
            # Move to next category
            category_index += 1
            
            # Remove empty lists
            category_lists = [lst for lst in category_lists if lst]
            
            # Safety check: break if no more items
            if not category_lists:
                break
        
        # Sort final diverse set by score and return
        diverse_results.sort(key=lambda x: x["score"], reverse=True)
        return diverse_results[:limit]
    
    def _get_week_activity_summary(self, db: Session, user_id: int) -> Dict:
        """Get summary of user's activities this week"""
        from datetime import date, timedelta
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        week_activities = self.activity_repo.list_activities_between(
            db=db, user_id=user_id, start_day=week_start, end_day=today
        )
        
        # Analyze activity patterns
        exercise_activities = [a for a in week_activities if a.activity_category == "exercise"]
        sleep_activities = [a for a in week_activities if str(a.activity_name).lower() == "sleep"]
        
        # Calculate totals
        exercise_minutes = sum(int(a.duration_minutes or 0) for a in exercise_activities)
        exercise_days = len(set(a.created_at.date() for a in exercise_activities))
        sleep_days = len(sleep_activities)
        
        # Determine exercise done today
        today_exercises = [a for a in exercise_activities if a.created_at.date() == today]
        exercise_done_today = len(today_exercises) > 0
        
        # Calculate days into week (0=Monday, 6=Sunday)
        days_into_week = today.weekday()
        
        return {
            "exercise_minutes_week": exercise_minutes,
            "exercise_days": exercise_days,
            "exercise_done_today": exercise_done_today,
            "sleep_days": sleep_days,
            "days_into_week": days_into_week,
            "week_progress": "start" if days_into_week <= 1 else "mid" if days_into_week <= 4 else "end",
            "on_track": exercise_days >= (days_into_week // 2)  # Exercising every other day
        }
    
    def _enhance_context_with_activity(self, context: Dict, week_activities: Dict) -> Dict:
        """Enhance context with activity tracking data"""
        enhanced = context.copy()
        
        # Add activity tracking if not already present
        if "exercise_minutes_week" not in enhanced:
            enhanced["exercise_minutes_week"] = week_activities.get("exercise_minutes_week", 0)
        if "exercise_done_today" not in enhanced:
            enhanced["exercise_done_today"] = week_activities.get("exercise_done_today", False)
        if "week_progress" not in enhanced:
            enhanced["week_progress"] = week_activities.get("week_progress", "mid")
        if "on_track" not in enhanced:
            enhanced["on_track"] = week_activities.get("on_track", True)
        
        return enhanced
    
    def _score_content(
        self,
        content,
        context: Dict,
        recent_moods: List,
        user_interactions: List,
        week_activities: Dict
    ) -> float:
        """Score content from 0-100 based on multiple factors including activity tracking"""
        score = 50.0  # Base score
        
        # Factor 1: Mood match (±20 points)
        mood_bonus = self._calculate_mood_match(content, context, recent_moods)
        score += mood_bonus
        
        # Factor 2: Recency penalty (avoid recently viewed)
        if self._was_viewed_recently(content, user_interactions, days=3):
            score -= 25
        elif self._was_viewed_recently(content, user_interactions, days=7):
            score -= 10
        
        # Factor 3: Time availability match (±15 points)
        time_bonus = self._calculate_time_match(content, context)
        score += time_bonus
        
        # Factor 4: Energy level match (±15 points)
        energy_bonus = self._calculate_energy_match(content, context)
        score += energy_bonus
        
        # Factor 5: Time of day match (±10 points)
        time_of_day_bonus = self._calculate_time_of_day_match(content, context)
        score += time_of_day_bonus
        
        # Factor 6: Category filter (±20 points)
        category_bonus = self._calculate_category_match(content, context)
        score += category_bonus
        
        # Factor 7: Content type filter (±10 points)
        type_bonus = self._calculate_type_match(content, context)
        score += type_bonus
        
        # Factor 8: Success history (±15 points)
        success_bonus = self._calculate_success_bonus(content, user_interactions)
        score += success_bonus
        
        # Factor 9: ADAPTIVE - Activity-based recommendations (±25 points)
        activity_bonus = self._calculate_activity_bonus(content, context, week_activities)
        score += activity_bonus
        
        # Factor 10: ADAPTIVE - Week progress adjustments (±10 points)
        week_progress_bonus = self._calculate_week_progress_bonus(content, context, week_activities)
        score += week_progress_bonus
        
        return max(0, min(100, score))
    
    def _calculate_mood_match(self, content, context: Dict, recent_moods: List) -> float:
        """Match content to current mood"""
        mood = context.get("mood", "").lower()
        
        # If no mood in context, use most recent mood
        if not mood and recent_moods:
            mood = recent_moods[0].mood_label.lower()
        
        if not mood or not content.mood_tags:
            return 0
        
        try:
            mood_tags = json.loads(content.mood_tags) if isinstance(content.mood_tags, str) else content.mood_tags
        except:
            return 0
        
        # Direct match
        if mood in [tag.lower() for tag in mood_tags]:
            return 20
        
        # Partial match (e.g., "very stressed" matches "stressed")
        for tag in mood_tags:
            if tag.lower() in mood or mood in tag.lower():
                return 15
        
        return 0
    
    def _calculate_time_match(self, content, context: Dict) -> float:
        """Match content to available time"""
        time_available = context.get("time_available")
        
        if not time_available or not content.duration_minutes:
            return 0
        
        duration = content.duration_minutes
        
        # Perfect fit (within 5 minutes)
        if abs(duration - time_available) <= 5:
            return 15
        
        # Fits within available time
        if duration <= time_available:
            return 10
        
        # Too long
        if duration > time_available:
            return -15
        
        return 0
    
    def _calculate_energy_match(self, content, context: Dict) -> float:
        """Match content to energy level"""
        energy = context.get("energy_level", "").lower()
        
        if not energy or not content.energy_level:
            return 0
        
        content_energy = content.energy_level.lower()
        
        # Direct match
        if energy == content_energy:
            return 15
        
        # Compatible matches
        if energy == "low" and content_energy in ["low", "medium"]:
            return 10
        if energy == "high" and content_energy in ["medium", "high"]:
            return 10
        
        # Mismatch
        if energy == "low" and content_energy == "high":
            return -15
        if energy == "high" and content_energy == "low":
            return -10
        
        return 0
    
    def _calculate_time_of_day_match(self, content, context: Dict) -> float:
        """Match content to time of day"""
        time_of_day = context.get("time_of_day", "").lower()
        
        if not time_of_day or not content.time_of_day:
            return 0
        
        content_time = content.time_of_day.lower()
        
        # "anytime" content always fits
        if content_time == "anytime":
            return 5
        
        # Direct match
        if time_of_day == content_time:
            return 10
        
        return 0
    
    def _calculate_category_match(self, content, context: Dict) -> float:
        """Match content to requested category"""
        category = context.get("category", "").lower()
        
        if not category:
            return 0
        
        if category in content.category_key.lower():
            return 20
        
        return -10
    
    def _calculate_type_match(self, content, context: Dict) -> float:
        """Match content to requested type"""
        content_type = context.get("content_type", "").lower()
        
        if not content_type:
            return 0
        
        if content_type == content.content_type.lower():
            return 10
        
        return -5
    
    def _was_viewed_recently(self, content, user_interactions: List, days: int) -> bool:
        """Check if content was viewed recently"""
        cutoff = datetime.now() - timedelta(days=days)
        
        for interaction in user_interactions:
            if interaction.content_id == content.id:
                if interaction.created_at >= cutoff:
                    return True
        
        return False
    
    def _calculate_success_bonus(self, content, user_interactions: List) -> float:
        """Boost content that user completed or rated highly"""
        for interaction in user_interactions:
            if interaction.content_id == content.id:
                # Completed content
                if interaction.interaction_type == "completed":
                    return 15
                # Highly rated
                if interaction.rating and interaction.rating >= 4:
                    return 10
                # Marked as helpful
                if interaction.was_helpful == 1:
                    return 12
        
        return 0
    
    def _calculate_activity_bonus(self, content, context: Dict, week_activities: Dict) -> float:
        """
        ADAPTIVE: Adjust recommendations based on user's actual activity behavior
        - If user hasn't exercised, boost cardio/strength content
        - If user already exercised today, boost recovery content
        - If low weekly exercise, encourage more activity
        """
        category = content.category_label.lower() if content.category_label else ""
        
        exercise_done_today = context.get("exercise_done_today", False)
        exercise_minutes_week = context.get("exercise_minutes_week", 0)
        on_track = context.get("on_track", True)
        
        # User hasn't exercised today - boost cardio/strength
        if not exercise_done_today:
            if "cardio" in category or "strength" in category:
                return 20  # Strong boost for exercise content
            elif "yoga" in category:
                return 10  # Moderate boost for gentle exercise
        
        # User already exercised today - boost recovery/wellness
        else:
            if "yoga" in category or "stretch" in category:
                return 15  # Boost recovery activities
            elif "meditation" in category or "sleep" in category:
                return 12  # Boost relaxation
            elif "cardio" in category or "strength" in category:
                return -15  # Discourage more intense exercise
        
        # User behind on weekly exercise goals
        if exercise_minutes_week < 60 and not on_track:  # Less than 1 hour/week
            if "cardio" in category or "strength" in category:
                return 15  # Encourage more activity
        
        # User on track or ahead
        elif exercise_minutes_week >= 150:  # Meeting WHO guidelines
            if "nutrition" in category or "meditation" in category:
                return 10  # Boost wellness content
        
        return 0
    
    def _calculate_week_progress_bonus(self, content, context: Dict, week_activities: Dict) -> float:
        """
        ADAPTIVE: Adjust recommendations based on where we are in the week
        - Start of week: Set the tone with energizing content
        - Mid-week: Maintain momentum, offer quick stress relief
        - End of week: Focus on recovery and preparation for next week
        """
        week_progress = context.get("week_progress", "mid")
        category = content.category_label.lower() if content.category_label else ""
        
        # Monday/Tuesday - Start strong
        if week_progress == "start":
            if "cardio" in category or "motivation" in category:
                return 10  # Boost energizing content
            elif "meditation" in category:
                return 8  # Morning mindfulness
        
        # Wednesday/Thursday - Midweek push
        elif week_progress == "mid":
            if "stress" in category:
                return 10  # Midweek stress relief
            elif "quick" in content.title.lower() or (content.duration_minutes and content.duration_minutes <= 10):
                return 8  # Quick sessions for busy midweek
        
        # Friday/Saturday/Sunday - Wind down & recover
        elif week_progress == "end":
            if "yoga" in category or "sleep" in category:
                return 10  # Recovery and rest
            elif "nutrition" in category:
                return 8  # Meal prep for next week
            elif "cardio" in category or "strength" in category:
                return -5  # Slight decrease for intense exercise
        
        return 0
    
    def _generate_reason(self, content, context: Dict, user_interactions: List, week_activities: Dict) -> str:
        """Generate human-readable reason for suggestion"""
        reasons = []
        
        # Get content details for more specific reasons
        category = content.category_label.lower() if content.category_label else ""
        title = content.title.lower() if content.title else ""
        content_type = content.content_type.lower() if content.content_type else ""
        
        # ADAPTIVE: Add activity-based context to reasons
        exercise_done_today = context.get("exercise_done_today", False)
        exercise_minutes_week = context.get("exercise_minutes_week", 0)
        week_progress = context.get("week_progress", "mid")
        
        # Activity-specific reasons
        if not exercise_done_today and ("cardio" in category or "strength" in category):
            reasons.append("No exercise yet today - let's get moving!")
        elif exercise_done_today and ("yoga" in category or "meditation" in category):
            reasons.append("Great recovery after your workout")
        
        # Week progress reasons
        if week_progress == "start" and "cardio" in category:
            reasons.append("Start your week strong")
        elif week_progress == "end" and ("sleep" in category or "yoga" in category):
            reasons.append("Perfect weekend recovery")
        
        # Mood match - make it specific to content
        mood = context.get("mood")
        if mood and content.mood_tags and len(reasons) < 2:
            try:
                mood_tags = json.loads(content.mood_tags) if isinstance(content.mood_tags, str) else content.mood_tags
                if mood.lower() in [tag.lower() for tag in mood_tags]:
                    # Make reason specific to the category
                    if "meditation" in category:
                        reasons.append(f"Calms {mood} feelings through mindfulness")
                    elif "yoga" in category:
                        reasons.append(f"Relieves {mood} tension with gentle movement")
                    elif "cardio" in category or "exercise" in category:
                        reasons.append(f"Releases {mood} energy through exercise")
                    elif "sleep" in category:
                        reasons.append(f"Helps with {mood} feelings for better rest")
                    elif "stress" in category:
                        reasons.append(f"Quick relief for {mood} moments")
                    else:
                        reasons.append(f"Helpful for {mood} mood")
            except:
                pass
        
        # Time match - make it more specific
        if context.get("time_available") and content.duration_minutes and len(reasons) < 2:
            if content.duration_minutes <= context["time_available"]:
                if content.duration_minutes <= 5:
                    reasons.append(f"Quick {content.duration_minutes}-min session")
                elif content.duration_minutes <= 15:
                    reasons.append(f"Fits in just {content.duration_minutes} minutes")
                else:
                    reasons.append(f"{content.duration_minutes}-min commitment")
        
        # Success history
        if len(reasons) < 2:
            for interaction in user_interactions:
                if interaction.content_id == content.id:
                    if interaction.was_helpful == 1:
                        reasons.append("Worked well for you before")
                        break
        
        # Category-specific defaults if no other reasons
        if not reasons:
            if "meditation" in category:
                if "stress" in title or "anxiety" in title:
                    reasons.append("Proven stress reduction technique")
                else:
                    reasons.append("Builds mindfulness practice")
            elif "yoga" in category:
                if "desk" in title or "office" in title:
                    reasons.append("Perfect for desk workers")
                else:
                    reasons.append("Improves flexibility and balance")
            elif "cardio" in category:
                if "hiit" in title:
                    reasons.append("High-impact workout for results")
                elif "office" in title or "desk" in title:
                    reasons.append("Office-friendly exercises")
                else:
                    reasons.append("Boosts cardiovascular health")
            elif "strength" in category:
                reasons.append("Builds muscle and strength")
            elif "sleep" in category:
                reasons.append("Improves sleep quality")
            elif "stress" in category:
                if "breathing" in title:
                    reasons.append("Fast-acting breathing technique")
                else:
                    reasons.append("Evidence-based stress management")
            elif "nutrition" in category:
                if "recipe" in title:
                    reasons.append("Healthy meal ideas")
                elif "meal prep" in title:
                    reasons.append("Efficient meal planning")
                else:
                    reasons.append("Practical nutrition guidance")
            else:
                # Generic fallback
                if content.difficulty:
                    reasons.append(f"{content.difficulty.capitalize()}-level {content_type}")
                else:
                    reasons.append(f"Recommended {content_type}")
        
        return " • ".join(reasons[:2])
