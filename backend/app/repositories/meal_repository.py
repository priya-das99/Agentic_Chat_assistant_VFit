from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.db_models import MealLog


class MealRepository:
    def create_meal_log(
        self,
        db: Session,
        user_id: int,
        meal_type: str,
        calories: int,
        meal_name: str | None = None,
        protein_grams: int | None = None,
        carbs_grams: int | None = None,
        fat_grams: int | None = None,
        notes: str | None = None,
        created_at: datetime | None = None,
    ) -> MealLog:
        meal_log = MealLog(
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
        db.add(meal_log)
        db.commit()
        db.refresh(meal_log)
        return meal_log
    
    def get_meals_for_day(self, db: Session, user_id: int, day: date | None = None) -> list[MealLog]:
        day = day or date.today()
        return (
            db.query(MealLog)
            .filter(
                MealLog.user_id == user_id,
                func.date(MealLog.created_at) == day.isoformat(),
            )
            .order_by(MealLog.created_at.desc())
            .all()
        )
    
    def get_total_calories_for_day(self, db: Session, user_id: int, day: date | None = None) -> int:
        day = day or date.today()
        total = (
            db.query(func.coalesce(func.sum(MealLog.calories), 0))
            .filter(
                MealLog.user_id == user_id,
                func.date(MealLog.created_at) == day.isoformat(),
            )
            .scalar()
        )
        return int(total or 0)
    
    def get_recent_meals(self, db: Session, user_id: int, limit: int = 10) -> list[MealLog]:
        return (
            db.query(MealLog)
            .filter(MealLog.user_id == user_id)
            .order_by(MealLog.created_at.desc())
            .limit(limit)
            .all()
        )
