from sqlalchemy.orm import Session

from app.models.api_models import ActivityDecisionResult, ActivityLogInput
from app.services.activity_service import ActivityService

activity_service = ActivityService()


def log_activity_tool(
    db: Session,
    user_id: int,
    activity_name: str,
    value: float | None = None,
    unit: str | None = None,
    duration_minutes: int | None = None,
    notes: str | None = None,
) -> dict:
    activity_input = ActivityLogInput(
        activity_name=activity_name,
        value=value,
        unit=unit,
        duration_minutes=duration_minutes,
        notes=notes,
    )
    activity_log = activity_service.log_activity(
        db=db,
        user_id=user_id,
        activity_name=activity_input.activity_name,
        value=activity_input.value,
        unit=activity_input.unit,
        duration_minutes=activity_input.duration_minutes,
        notes=activity_input.notes,
    )

    return {
        "success": True,
        "activity_id": activity_log.id,
        "activity_category": activity_log.activity_category,
        "activity_name": activity_log.activity_name,
        "value": activity_log.value,
        "unit": activity_log.unit,
        "duration_minutes": activity_log.duration_minutes,
        "notes": activity_log.notes,
        "message": "Activity logged successfully",
    }


def get_recent_activities_tool(db: Session, user_id: int, limit: int = 5) -> dict:
    activities = activity_service.get_recent_activities(db=db, user_id=user_id, limit=limit)
    return {
        "items": [
            {
                "activity_category": activity.activity_category,
                "activity_name": activity.activity_name,
                "value": activity.value,
                "unit": activity.unit,
                "duration_minutes": activity.duration_minutes,
                "notes": activity.notes,
                "created_at": activity.created_at.isoformat() if activity.created_at else None,
            }
            for activity in activities
        ]
    }


def parse_activity_message_tool(message: str) -> dict:
    result = activity_service.analyze_activity_message(message).model_dump()
    # Add instruction based on what actions are present
    if result.get("actions"):
        has_log = any(a.get("action") in ["log", "update"] for a in result["actions"])
        has_clarify = any(a.get("action") in ["clarify", "confirm"] for a in result["actions"])
        
        if has_clarify:
            result["instruction"] = "Ask the clarification question and STOP. Do not call apply_activity_decision yet."
        elif has_log:
            result["instruction"] = "Call apply_activity_decision ONCE with this result, then STOP."
    return result


def apply_activity_decision_tool(db: Session, user_id: int, decision_json: str) -> dict:
    normalized = ActivityDecisionResult.model_validate_json(decision_json)
    result = activity_service.apply_activity_decision_result(
        db=db,
        user_id=user_id,
        decision=normalized,
    )
    
    # Add fitness summary and wellness suggestions for exercise activities
    fitness_info = []
    for applied in result.get("applied", []):
        if applied.get("entity") == "activity" and applied.get("activity_name"):
            # Get the logged activity
            activity_log = activity_service.get_latest_activity_for_day(
                db=db, 
                user_id=user_id, 
                activity_name=applied["activity_name"]
            )
            
            if activity_log and activity_log.activity_category == "exercise":
                # Get fitness summary
                summary = activity_service.get_fitness_summary(db, user_id, activity_log)
                suggestions = activity_service.get_wellness_suggestions(db, user_id, activity_log)
                
                fitness_info.append({
                    "activity_name": applied["activity_name"],
                    "fitness_summary": summary,
                    "wellness_suggestions": suggestions
                })
    
    result["fitness_info"] = fitness_info
    result["success"] = True
    result["instruction"] = "TASK COMPLETE. Present the activity result with fitness metrics and wellness suggestions, then STOP. Do not call any more tools."
    return result
