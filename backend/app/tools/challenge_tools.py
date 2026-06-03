from app.services.challenge_service import ChallengeService

challenge_service = ChallengeService()


def get_current_challenges_tool(db, user_id: int) -> dict:
    summary = challenge_service.get_summary(db=db, user_id=user_id)
    return {
        "week_start": summary["week_start"],
        "week_end": summary["week_end"],
        "active_challenges": summary["active_challenges"],
        "total_points": summary["total_points"],
        "message": summary["message"],
        "summary_text": summary.get("summary_text") or challenge_service.format_chat_summary_text(summary),
    }


def get_challenge_summary_tool(db, user_id: int) -> dict:
    summary = challenge_service.get_summary(db=db, user_id=user_id)
    summary["summary_text"] = summary.get("summary_text") or challenge_service.format_chat_summary_text(summary)
    return summary


def get_challenge_coach_snapshot_tool(db, user_id: int, message: str) -> dict:
    return challenge_service.get_coach_snapshot(db=db, user_id=user_id, message=message)


def get_challenge_reminders_tool(db, user_id: int) -> dict:
    reminders = challenge_service.get_reminders(db=db, user_id=user_id)
    return {
        "user_id": user_id,
        "reminders": reminders,
        "message": reminders[0]["message"] if reminders else "No reminders right now.",
    }


def record_challenge_progress_tool(
    db,
    user_id: int,
    challenge_code: str | None = None,
    metric_key: str | None = None,
    value: int | None = None,
    message: str | None = None,
) -> dict:
    key = metric_key or challenge_code
    if not key:
        return {"updated": False, "reason": "missing_metric_key"}

    result = challenge_service.record_signal(
        db=db,
        user_id=user_id,
        metric_key=key,
        challenge_code=challenge_code,
        value=value,
        message=message,
    )
    return result


def record_step_progress_tool(db, user_id: int, steps: int, message: str | None = None) -> dict:
    return challenge_service.record_step_progress(db=db, user_id=user_id, steps=steps, message=message)
