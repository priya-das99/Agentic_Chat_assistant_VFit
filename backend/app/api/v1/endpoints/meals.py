from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.meal_service import MealService
from app.services.nutrition_estimator import nutrition_estimator

router = APIRouter()
meal_service = MealService()


class EstimateRequest(BaseModel):
    meal_name: str
    servings: float = 1.0
    meal_type: str | None = None


class MealLogRequest(BaseModel):
    user_id: int
    meal_type: str
    meal_name: str
    calories: int
    protein_grams: int | None = None
    carbs_grams: int | None = None
    fat_grams: int | None = None
    notes: str | None = None


@router.post("/estimate")
def estimate_nutrition(request: EstimateRequest):
    """AI-powered nutrition estimation"""
    estimate = nutrition_estimator.estimate(
        meal_name=request.meal_name,
        servings=request.servings,
        meal_type=request.meal_type
    )
    
    return {
        "calories": estimate.calories,
        "protein_grams": estimate.protein_grams,
        "carbs_grams": estimate.carbs_grams,
        "fat_grams": estimate.fat_grams,
        "confidence": estimate.confidence,
        "notes": estimate.notes
    }


@router.post("/log")
def log_meal(request: MealLogRequest, db: Session = Depends(get_db)):
    """Log a meal with nutrition information"""
    meal_log = meal_service.log_meal(
        db=db,
        user_id=request.user_id,
        meal_type=request.meal_type,
        meal_name=request.meal_name,
        calories=request.calories,
        protein_grams=request.protein_grams,
        carbs_grams=request.carbs_grams,
        fat_grams=request.fat_grams,
        notes=request.notes
    )
    
    return {
        "success": True,
        "meal_id": meal_log.id,
        "calories": meal_log.calories,
        "message": f"Logged {meal_log.meal_name} ({meal_log.calories} calories)"
    }


@router.get("/search")
def search_foods(query: str):
    """Search for foods in database (autocomplete)"""
    results = nutrition_estimator.search_foods(query, limit=10)
    return {"foods": results}


@router.get("/today")
def get_today_meals(user_id: int = 1, db: Session = Depends(get_db)):
    """Get today's meal summary"""
    summary = meal_service.get_daily_meal_summary(db=db, user_id=user_id)
    return summary
