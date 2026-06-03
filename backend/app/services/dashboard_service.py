from __future__ import annotations

import json
from datetime import date, timedelta

from app.repositories.activity_catalog_repository import ActivityCatalogRepository
from app.repositories.activity_repository import ActivityRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.mood_repository import MoodRepository
from app.repositories.meal_repository import MealRepository
from app.services.activity_service import ActivityService
from app.services.challenge_service import ChallengeService
from app.services.profile_service import ProfileService
from app.services.recommendation_service import RecommendationService


class DashboardService:
    def __init__(self):
        self.chat_repository = ChatRepository()
        self.activity_repository = ActivityRepository()
        self.mood_repository = MoodRepository()
        self.meal_repository = MealRepository()
        self.activity_catalog_repository = ActivityCatalogRepository()
        self.activity_service = ActivityService()
        self.challenge_service = ChallengeService()
        self.profile_service = ProfileService()
        self.recommendation_service = RecommendationService()

    def get_overview(self, db, user_id: int, reference_date: date | None = None) -> dict:
        reference_date = reference_date or date.today()
        week_start = reference_date - timedelta(days=reference_date.weekday())
        week_end = week_start + timedelta(days=6)

        self.chat_repository.get_or_create_user(db=db, user_id=user_id)
        profile = self.profile_service.get_or_create_profile(db=db, user_id=user_id)
        challenge_summary = self.challenge_service.get_summary(db=db, user_id=user_id, reference_date=reference_date)

        today_moods = self.mood_repository.list_moods_for_day(db=db, user_id=user_id, day=reference_date)
        today_activities = self.activity_repository.list_activities_for_day(db=db, user_id=user_id, day=reference_date)
        week_moods = self.mood_repository.list_moods_between(db=db, user_id=user_id, start_day=week_start, end_day=week_end)
        week_activities = self.activity_repository.list_activities_between(db=db, user_id=user_id, start_day=week_start, end_day=week_end)

        return {
            "user_id": user_id,
            "date": reference_date.isoformat(),
            "daily_stats": self._build_daily_stats(
                db=db,
                user_id=user_id,
                reference_date=reference_date,
                today_moods=today_moods,
                today_activities=today_activities,
            ),
            "calorie_balance": self.get_calorie_balance(db=db, user_id=user_id, reference_date=reference_date),
            "today_logs": self._build_today_logs(today_moods=today_moods, today_activities=today_activities),
            "weekly_snapshot": self._build_weekly_snapshot(
                week_start=week_start,
                week_end=week_end,
                week_moods=week_moods,
                week_activities=week_activities,
                challenge_summary=challenge_summary,
            ),
            "suggestions": self._build_suggestions(
                db=db,
                week_moods=week_moods,
                week_activities=week_activities,
                profile=profile,
                challenge_summary=challenge_summary,
            ),
        }
    
    def get_calorie_balance(self, db, user_id: int, reference_date: date | None = None) -> dict:
        """
        Calculate calorie balance for the dashboard display.
        Formula: Balance = Meals - Resting (BMR) - Active
        
        Returns:
            Dict with target, meals, resting_bmr, active_calories, balance, total_steps
        """
        reference_date = reference_date or date.today()
        
        # Get user profile for BMR calculation
        profile = self.profile_service.get_or_create_profile(db=db, user_id=user_id)
        
        # Calculate BMR (Basal Metabolic Rate) - calories burned at rest
        resting_bmr = self._calculate_bmr(
            weight_kg=profile.weight_kg if profile and profile.weight_kg else 70,
            age=profile.age if profile and profile.age else 30,
            gender=profile.gender if profile and profile.gender else "male"
        )
        
        # Get fitness metrics from today's activities
        fitness_metrics = self.activity_service.get_daily_fitness_metrics(
            db=db, 
            user_id=user_id, 
            day=reference_date
        )
        
        active_calories = fitness_metrics.get("total_calories", 0)
        total_steps = fitness_metrics.get("total_steps", 0)
        
        # Get meal calories from today's meals
        meals_intake = self.meal_repository.get_total_calories_for_day(
            db=db,
            user_id=user_id,
            day=reference_date
        )
        
        # Target calories (maintenance = BMR + Active)
        target_calories = int(resting_bmr + active_calories)
        
        # Balance calculation: Meals - Resting - Active
        balance = meals_intake - resting_bmr - active_calories
        
        return {
            "target": target_calories,
            "meals": meals_intake,
            "resting_bmr": int(resting_bmr),
            "active_calories": int(active_calories),
            "balance": int(balance),
            "total_steps": total_steps,
            "date": reference_date.isoformat()
        }
    
    def _calculate_bmr(self, weight_kg: float, age: int, gender: str) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation.
        This is the number of calories burned at rest per day.
        
        Args:
            weight_kg: Weight in kilograms
            age: Age in years
            gender: "male" or "female"
            
        Returns:
            BMR in calories per day
        """
        # Mifflin-St Jeor Equation
        # Men: BMR = 10 × weight(kg) + 6.25 × height(cm) − 5 × age(y) + 5
        # Women: BMR = 10 × weight(kg) + 6.25 × height(cm) − 5 × age(y) − 161
        
        # Simplified version without height (use average height: 170cm)
        # This gives a reasonable approximation
        average_height_cm = 170
        
        if gender.lower() == "female":
            bmr = (10 * weight_kg) + (6.25 * average_height_cm) - (5 * age) - 161
        else:  # male or default
            bmr = (10 * weight_kg) + (6.25 * average_height_cm) - (5 * age) + 5
        
        return max(bmr, 1200)  # Minimum BMR of 1200 calories

    def _build_daily_stats(self, db, user_id: int, reference_date: date, today_moods: list, today_activities: list) -> list[dict]:
        water_total_ml = self.activity_service.get_total_value_for_day(db=db, user_id=user_id, activity_name="water", day=reference_date)
        sleep_log = self.activity_service.get_latest_activity_for_day(db=db, user_id=user_id, activity_name="sleep", day=reference_date)
        exercise_minutes = sum(int(activity.duration_minutes or 0) for activity in today_activities if activity.activity_category == "exercise")
        
        # Get fitness metrics (steps and calories) - these go to calorie balance, not daily stats
        fitness_metrics = self.activity_service.get_daily_fitness_metrics(db=db, user_id=user_id, day=reference_date)
        total_steps = fitness_metrics.get("total_steps", 0)
        total_calories = fitness_metrics.get("total_calories", 0)
        
        # Convert water from ml to glasses (1 glass = 250ml)
        water_glasses = round(water_total_ml / 250, 1) if water_total_ml else 0
        water_display = f"{water_glasses} glasses" if water_glasses else "0 glasses"
        
        # Convert exercise from minutes to hours
        exercise_hours = round(exercise_minutes / 60, 1) if exercise_minutes else 0
        exercise_display = f"{exercise_hours} h" if exercise_hours else "0 h"
        
        return [
            {
                "label": "Mood check-ins",
                "value": str(len(today_moods)),
                "detail": "Entries logged today",
                "tone": "calm" if today_moods else "soft",
            },
            {
                "label": "Water",
                "value": water_display,
                "detail": "Hydration logged today",
                "tone": "fresh" if water_total_ml else "soft",
            },
            {
                "label": "Sleep",
                "value": f"{sleep_log.value} h" if sleep_log and sleep_log.value is not None else "No log",
                "detail": "Latest sleep entry",
                "tone": "rest" if sleep_log else "soft",
            },
            {
                "label": "Exercise",
                "value": exercise_display,
                "detail": f"{sum(1 for activity in today_activities if activity.activity_category == 'exercise')} sessions today",
                "tone": "energy" if exercise_minutes else "soft",
            },
        ]

    def _build_today_logs(self, today_moods: list, today_activities: list) -> list[dict]:
        entries: list[dict] = []

        for mood in today_moods:
            mood_emoji = self._get_mood_emoji(mood.mood_label)
            entries.append(
                {
                    "item_type": "mood",
                    "title": f"{mood_emoji} {str(mood.mood_label).title()} mood",
                    "detail": mood.reason or "Mood check-in recorded.",
                    "created_at": mood.created_at.isoformat() if mood.created_at else None,
                }
            )

        for activity in today_activities:
            activity_emoji = self._get_activity_emoji(activity.activity_name, activity.activity_category)
            entries.append(
                {
                    "item_type": activity.activity_category or "activity",
                    "title": f"{activity_emoji} {str(activity.activity_name).replace('_', ' ').title()}",
                    "detail": self._activity_detail(activity),
                    "created_at": activity.created_at.isoformat() if activity.created_at else None,
                }
            )

        entries.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return entries

    def _build_weekly_snapshot(self, week_start: date, week_end: date, week_moods: list, week_activities: list, challenge_summary: dict) -> dict:
        active_challenges = challenge_summary.get("active_challenges", [])
        
        # Calculate weekly points from the challenge summary
        weekly_points = challenge_summary.get("weekly_points", 0)
        
        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "mood_logs": len(week_moods),
            "activity_sessions": len(week_activities),
            "exercise_minutes": sum(int(activity.duration_minutes or 0) for activity in week_activities if activity.activity_category == "exercise"),
            "completed_challenges": sum(1 for challenge in active_challenges if challenge.get("status") == "completed"),
            "total_points": weekly_points,
        }

    def _build_suggestions(self, db, week_moods: list, week_activities: list, profile, challenge_summary: dict) -> list[dict]:
        """
        AGENTIC SUGGESTIONS: Uses smart recommendation service with personalized scoring
        based on user's weekly data, mood patterns, and activity history.
        """
        # Analyze user's weekly state
        avg_mood = self._calculate_average_mood(week_moods)
        exercise_minutes = sum(int(activity.duration_minutes or 0) for activity in week_activities if activity.activity_category == "exercise")
        sleep_logs = sum(1 for activity in week_activities if str(activity.activity_name).lower() == "sleep")
        
        # Determine user's current need based on weekly data
        primary_need = self._determine_primary_need(
            mood_count=len(week_moods),
            avg_mood=avg_mood,
            exercise_minutes=exercise_minutes,
            sleep_logs=sleep_logs,
            challenge_summary=challenge_summary
        )
        
        # Build context for recommendation service
        context = {
            "user_mood": avg_mood,
            "user_energy": self._estimate_energy_level(exercise_minutes, sleep_logs),
            "time_available": 15,  # Default to 15 min for dashboard suggestions
            "user_goals": [primary_need],
            "user_preferences": getattr(profile, "preferred_activities", "").split(",") if profile else []
        }
        
        # Get smart recommendations from content library
        recommendations = self.recommendation_service.get_personalized_content(
            db=db,
            user_id=profile.user_id if profile else 1,
            context=context,
            limit=5
        )
        
        # Transform recommendations to dashboard format with agentic reasoning
        suggestions = []
        for rec in recommendations:
            reason = self._generate_agentic_reason(
                content=rec,
                primary_need=primary_need,
                week_moods=week_moods,
                exercise_minutes=exercise_minutes,
                sleep_logs=sleep_logs
            )
            
            suggestions.append({
                "content_id": rec.get("id"),
                "title": rec.get("title", "Wellness Activity"),
                "category_label": rec.get("category_label", "Exercise"),
                "content_type": rec.get("content_type", "Video"),
                "duration": f"{rec['duration_minutes']} min" if rec.get('duration_minutes') else "15 min",
                "url": rec.get("url", ""),
                "reason": reason,
                "score": rec.get("score", 0),
                "action_prompt": f"Try this: {rec.get('title', 'this activity')}"
            })
        
        # Return top 3 suggestions from the diverse set
        return suggestions[:3]
    
    def _calculate_average_mood(self, week_moods: list) -> str:
        """Calculate average mood from weekly mood logs"""
        if not week_moods:
            return "neutral"
        
        mood_scores = {
            "great": 5, "happy": 4, "good": 4, "neutral": 3, "ok": 3,
            "sad": 2, "stressed": 2, "anxious": 2, "angry": 1, "tired": 2
        }
        
        total_score = sum(mood_scores.get(str(mood.mood_label).lower(), 3) for mood in week_moods)
        avg_score = total_score / len(week_moods)
        
        if avg_score >= 4.5:
            return "great"
        elif avg_score >= 3.5:
            return "good"
        elif avg_score >= 2.5:
            return "neutral"
        else:
            return "stressed"
    
    def _estimate_energy_level(self, exercise_minutes: int, sleep_logs: int) -> str:
        """Estimate energy level from activity data"""
        if exercise_minutes > 150 and sleep_logs >= 5:
            return "high"
        elif exercise_minutes > 60 or sleep_logs >= 3:
            return "medium"
        else:
            return "low"
    
    def _determine_primary_need(self, mood_count: int, avg_mood: str, exercise_minutes: int, 
                                 sleep_logs: int, challenge_summary: dict) -> str:
        """
        AGENTIC DECISION: Determine what the user needs most based on weekly data
        This is the "intelligence" that makes suggestions feel personalized
        """
        # Priority 1: Mental health (if mood is low or not tracking)
        if avg_mood in ["stressed", "sad", "anxious"] or mood_count < 3:
            return "stress_relief"
        
        # Priority 2: Sleep/recovery (if not sleeping enough)
        if sleep_logs < 3:
            return "better_sleep"
        
        # Priority 3: Exercise (if below recommended weekly minutes)
        if exercise_minutes < 90:
            return "more_movement"
        
        # Priority 4: Challenge support (if active challenge exists)
        active_challenges = challenge_summary.get("active_challenges", [])
        incomplete_challenges = [c for c in active_challenges if c.get("status") != "completed"]
        if incomplete_challenges:
            return "challenge_support"
        
        # Default: General wellness
        return "maintain_wellness"
    
    def _generate_agentic_reason(self, content: dict, primary_need: str, week_moods: list, 
                                  exercise_minutes: int, sleep_logs: int) -> str:
        """
        AGENTIC REASONING: Generate personalized explanation for why this content is suggested.
        Each suggestion gets a unique reason based on the ACTUAL content category.
        """
        mood_count = len(week_moods)
        content_title = content.get('title', '').lower()
        content_category = content.get('category_label', '').lower()
        
        # Primary logic: Check content category FIRST to give specific reasons
        
        # MEDITATION & MINDFULNESS
        if 'meditation' in content_category or 'mindfulness' in content_category:
            if mood_count == 0:
                return "Start your mindfulness journey. Regular meditation builds emotional awareness."
            elif 'stress' in content_title.lower():
                return "Your mood patterns suggest stress. This meditation helps calm your mind."
            else:
                return "A mindfulness practice to enhance mental clarity and emotional balance."
        
        # YOGA & STRETCHING
        elif 'yoga' in content_category or 'stretch' in content_category:
            if 'desk' in content_title or 'office' in content_title:
                return "Office-friendly stretches to stay active during your workday."
            elif exercise_minutes < 30:
                return f"Add flexibility and movement with {content.get('duration_minutes', 15)} minutes of yoga."
            else:
                return "Complement your exercise routine with restorative yoga practice."
        
        # CARDIO & EXERCISES
        elif 'cardio' in content_category or 'exercise' in content_category:
            if exercise_minutes == 0:
                return "No exercise yet this week. Start with this quick, effective workout!"
            elif 'full body' in content_title:
                return "A comprehensive workout to boost energy and build fitness."
            elif 'hiit' in content_title.lower():
                return "High-intensity training for maximum results in minimal time."
            elif '7 exercises' in content_title or '42' in content_title:
                return "Practical exercises you can do anywhere, anytime."
            else:
                return f"Boost your activity level with this {content.get('duration_minutes', 15)}-minute workout."
        
        # STRENGTH TRAINING
        elif 'strength' in content_category:
            return "Build muscle and strength with proper techniques and progressions."
        
        # SLEEP & RELAXATION
        elif 'sleep' in content_category or 'wind' in content_title or 'hypnosis' in content_title:
            if sleep_logs == 0:
                return "Establish healthy sleep habits with this guided relaxation session."
            elif sleep_logs < 3:
                return "Improve your sleep quality with a proven wind-down routine."
            else:
                return "Maintain your sleep consistency with this relaxation practice."
        
        # STRESS RELIEF
        elif 'stress' in content_category or 'anxiety' in content_category or 'breathing' in content_category:
            if 'breathing' in content_title.lower():
                return "Quick breathing techniques to instantly calm anxiety and stress."
            else:
                return "Evidence-based stress management for daily wellbeing."
        
        # NUTRITION
        elif 'nutrition' in content_category or 'recipe' in content_category or 'meal' in content_category:
            return "Develop healthy eating habits with practical nutrition guidance."
        
        # FALLBACK: Generic based on primary need
        else:
            if primary_need == "stress_relief":
                return "Recommended to help you manage stress and find calm this week."
            elif primary_need == "better_sleep":
                return "Support better sleep quality and restful nights."
            elif primary_need == "more_movement":
                return "Increase your activity and build a consistent exercise habit."
            elif primary_need == "challenge_support":
                return "Perfect for supporting your active wellness challenges."
            else:
                return "A personalized wellness recommendation for your week."

    def _suggestion_item(self, *, row, reason: str) -> dict:
        return {
            "title": row.activity_label,
            "category_label": row.category_label,
            "reason": reason,
            "action_prompt": f"Can you suggest a simple {row.activity_label.lower()} routine for me today?",
        }

    def _activity_detail(self, activity) -> str:
        parts: list[str] = []
        
        # For sleep, prefer showing hours over minutes
        if str(activity.activity_name).lower() == "sleep":
            if activity.value is not None and activity.unit:
                value = f"{activity.value:g}" if isinstance(activity.value, float) else str(activity.value)
                parts.append(f"{value} {activity.unit}")
            elif activity.duration_minutes is not None:
                hours = activity.duration_minutes / 60
                parts.append(f"{hours:.1f} hours")
        else:
            # For other activities, show duration if available
            if activity.duration_minutes is not None:
                parts.append(f"{activity.duration_minutes} min")
            # Show value with unit
            if activity.value is not None and activity.unit:
                value = f"{activity.value:g}" if isinstance(activity.value, float) else str(activity.value)
                parts.append(f"{value} {activity.unit}")
            elif activity.value is not None:
                parts.append(str(activity.value))
        
        # Always add notes if present
        if activity.notes:
            parts.append(str(activity.notes))
            
        return " • ".join(parts) if parts else "Logged today."

    def _parse_preferred_activities(self, preferred_activities: str | None) -> list[str]:
        if not preferred_activities:
            return []
        return [item.strip().lower() for item in preferred_activities.split(",") if item.strip()]

    def _row_aliases(self, row) -> set[str]:
        if not row.aliases:
            return set()
        try:
            return {str(alias).strip().lower() for alias in json.loads(row.aliases) if str(alias).strip()}
        except json.JSONDecodeError:
            return set()

    def _get_mood_emoji(self, mood_label: str) -> str:
        """Get emoji for mood label"""
        mood_map = {
            "great": "😄",
            "happy": "🙂",
            "good": "🙂",
            "neutral": "😐",
            "ok": "😐",
            "sad": "😔",
            "stressed": "😰",
            "anxious": "😟",
            "angry": "😠",
            "tired": "😴",
        }
        return mood_map.get(str(mood_label).lower(), "😊")

    def _get_activity_emoji(self, activity_name: str, activity_category: str | None) -> str:
        """Get emoji for activity"""
        activity_name_lower = str(activity_name).lower()
        category_lower = str(activity_category or "").lower()
        
        # Specific activities
        if "water" in activity_name_lower or "hydration" in activity_name_lower:
            return "💧"
        if "sleep" in activity_name_lower:
            return "😴"
        if "meditation" in activity_name_lower:
            return "🧘"
        if "yoga" in activity_name_lower:
            return "🧘‍♀️"
        if "run" in activity_name_lower or "jog" in activity_name_lower:
            return "🏃"
        if "walk" in activity_name_lower:
            return "🚶"
        if "cycle" in activity_name_lower or "bike" in activity_name_lower:
            return "🚴"
        if "swim" in activity_name_lower:
            return "🏊"
        if "stretch" in activity_name_lower:
            return "🤸"
        if "gym" in activity_name_lower or "weight" in activity_name_lower:
            return "🏋️"
        
        # Categories
        if "exercise" in category_lower or "cardio" in category_lower:
            return "💪"
        if "sport" in category_lower:
            return "⚽"
        if "wellbeing" in category_lower or "wellness" in category_lower:
            return "🌟"
        
        return "✓"
