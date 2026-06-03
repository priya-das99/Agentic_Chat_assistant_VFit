from datetime import datetime
from app.repositories.meal_repository import MealRepository


class MealService:
    def __init__(self):
        self.meal_repository = MealRepository()
    
    def log_meal(
        self,
        db,
        user_id: int,
        meal_type: str,
        calories: int,
        meal_name: str | None = None,
        protein_grams: int | None = None,
        carbs_grams: int | None = None,
        fat_grams: int | None = None,
        notes: str | None = None,
        created_at: datetime | None = None,
    ):
        """Log a meal with calorie information"""
        meal_log = self.meal_repository.create_meal_log(
            db=db,
            user_id=user_id,
            meal_type=meal_type,
            meal_name=meal_name,
            calories=calories,
            protein_grams=protein_grams,
            carbs_grams=carbs_grams,
            fat_grams=fat_grams,
            notes=notes,
            created_at=created_at,
        )
        return meal_log
    
    def get_daily_meal_summary(self, db, user_id: int, day=None) -> dict:
        """Get summary of today's meals"""
        meals = self.meal_repository.get_meals_for_day(db, user_id, day)
        total_calories = self.meal_repository.get_total_calories_for_day(db, user_id, day)
        
        # Breakdown by meal type
        breakdown = {
            "breakfast": 0,
            "lunch": 0,
            "dinner": 0,
            "snack": 0,
        }
        
        for meal in meals:
            meal_type = meal.meal_type.lower()
            if meal_type in breakdown:
                breakdown[meal_type] += meal.calories
        
        return {
            "total_calories": total_calories,
            "meal_count": len(meals),
            "breakdown": breakdown,
            "meals": [
                {
                    "id": meal.id,
                    "meal_type": meal.meal_type,
                    "meal_name": meal.meal_name,
                    "calories": meal.calories,
                    "created_at": meal.created_at.isoformat() if meal.created_at else None,
                }
                for meal in meals
            ]
        }
