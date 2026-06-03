from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.api_models import (
    ChallengeProgressRequest,
    ChallengeProgressResponse,
    ChallengeSummaryResponse,
    ChallengeTemplateItem,
    ReminderActionRequest,
)
from app.services.challenge_service import ChallengeService
from app.services.reminder_scheduler import ReminderScheduler

router = APIRouter()
challenge_service = ChallengeService()
reminder_scheduler = ReminderScheduler(interval_seconds=900)


@router.get("/summary", response_model=ChallengeSummaryResponse)
def get_challenge_summary(user_id: int = 1, db: Session = Depends(get_db)):
    summary = challenge_service.get_summary(db=db, user_id=user_id)
    return ChallengeSummaryResponse(**summary)


@router.get("/current", response_model=ChallengeSummaryResponse)
def get_current_challenges(user_id: int = 1, db: Session = Depends(get_db)):
    summary = challenge_service.get_summary(db=db, user_id=user_id)
    return ChallengeSummaryResponse(**summary)


@router.get("/templates", response_model=list[ChallengeTemplateItem])
def get_challenge_templates(db: Session = Depends(get_db)):
    templates = challenge_service.get_templates(db=db)
    return [ChallengeTemplateItem(**template) for template in templates]


@router.get("/reminders")
def get_challenge_reminders(user_id: int = 1, db: Session = Depends(get_db)):
    reminders = challenge_service.get_reminders(db=db, user_id=user_id)
    return {"user_id": user_id, "reminders": reminders}


@router.post("/progress", response_model=ChallengeProgressResponse)
def record_challenge_progress(request: ChallengeProgressRequest, db: Session = Depends(get_db)):
    result = challenge_service.record_signal(
        db=db,
        user_id=request.user_id,
        metric_key=request.metric_key or request.challenge_code or "",
        challenge_code=request.challenge_code,
        value=request.value,
        message=request.message,
    )
    return ChallengeProgressResponse(**result)


@router.post("/reminders/{reminder_id}/complete")
def complete_reminder(reminder_id: int, request: ReminderActionRequest, db: Session = Depends(get_db)):
    reminder = challenge_service.complete_reminder(db=db, reminder_id=reminder_id, user_id=request.user_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"ok": True, "reminder": reminder}


@router.post("/reminders/{reminder_id}/dismiss")
def dismiss_reminder(reminder_id: int, request: ReminderActionRequest, db: Session = Depends(get_db)):
    reminder = challenge_service.dismiss_reminder(db=db, reminder_id=reminder_id, user_id=request.user_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"ok": True, "reminder": reminder}


@router.post("/reminders/{reminder_id}/snooze")
def snooze_reminder(reminder_id: int, request: ReminderActionRequest, db: Session = Depends(get_db)):
    reminder = challenge_service.snooze_reminder(
        db=db,
        reminder_id=reminder_id,
        user_id=request.user_id,
        snooze_minutes=request.snooze_minutes,
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"ok": True, "reminder": reminder}


@router.post("/reminders/run")
async def run_reminder_cycle(db: Session = Depends(get_db)):
    created = reminder_scheduler.reminder_service.run_cycle(db=db)
    return {"ok": True, "created": created}
