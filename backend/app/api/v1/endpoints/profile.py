from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.profile_service import ProfileService

router = APIRouter()
profile_service = ProfileService()


class UpdateTimezoneRequest(BaseModel):
    timezone: str


class ProfileResponse(BaseModel):
    user_id: int
    age: int | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    fitness_goal: str | None = None
    activity_level: str | None = None

    class Config:
        from_attributes = True


@router.get("/", response_model=ProfileResponse)
def get_profile(user_id: int = 1, db: Session = Depends(get_db)):
    profile = profile_service.get_or_create_profile(db=db, user_id=user_id)
    return ProfileResponse(
        user_id=profile.user_id,
        age=profile.age,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        fitness_goal=profile.fitness_goal,
        activity_level=profile.activity_level,
    )


@router.patch("/timezone", response_model=dict)
def update_timezone(request: UpdateTimezoneRequest, user_id: int = 1, db: Session = Depends(get_db)):
    # For now, just acknowledge the timezone update
    # In a future migration, this will store timezone in the database
    return {
        "success": True,
        "message": f"Timezone {request.timezone} noted (storage pending database migration)",
        "timezone": request.timezone
    }
