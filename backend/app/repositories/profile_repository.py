from sqlalchemy.orm import Session

from app.models.db_models import UserProfile


class ProfileRepository:
    def get_profile(self, db: Session, user_id: int) -> UserProfile | None:
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def create_profile(
        self,
        db: Session,
        user_id: int,
        age: int | None = None,
        height_cm: int | None = None,
        weight_kg: int | None = None,
        fitness_goal: str | None = None,
        activity_level: str | None = None,
        preferred_activities: str | None = None,
        limitations: str | None = None,
    ) -> UserProfile:
        profile = UserProfile(
            user_id=user_id,
            age=age,
            height_cm=height_cm,
            weight_kg=weight_kg,
            fitness_goal=fitness_goal,
            activity_level=activity_level,
            preferred_activities=preferred_activities,
            limitations=limitations,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def update_profile(self, db: Session, profile: UserProfile, **fields) -> UserProfile:
        for key, value in fields.items():
            setattr(profile, key, value)
        db.commit()
        db.refresh(profile)
        return profile
