from app.repositories.profile_repository import ProfileRepository


class ProfileService:
    def __init__(self):
        self.profile_repository = ProfileRepository()

    def get_or_create_profile(self, db, user_id: int):
        profile = self.profile_repository.get_profile(db=db, user_id=user_id)
        if profile:
            return profile

        return self.profile_repository.create_profile(
            db=db,
            user_id=user_id,
            fitness_goal="improve fitness consistency",
            activity_level="intermediate",
            preferred_activities="badminton, walking",
            limitations="none",
        )

    def format_profile_summary(self, profile) -> str:
        lines = []
        if profile.fitness_goal:
            lines.append(f"- goal: {profile.fitness_goal}")
        if profile.activity_level:
            lines.append(f"- activity level: {profile.activity_level}")
        if profile.preferred_activities:
            lines.append(f"- preferred activities: {profile.preferred_activities}")
        if profile.limitations:
            lines.append(f"- limitations: {profile.limitations}")

        return "\n".join(lines) if lines else "No structured profile yet."
