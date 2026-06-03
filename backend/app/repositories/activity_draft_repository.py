import json
from datetime import date, time

from sqlalchemy.orm import Session

from app.models.db_models import SessionActivityDraft


class ActivityDraftRepository:
    def get_by_session_id(self, db: Session, session_id: int) -> SessionActivityDraft | None:
        return db.query(SessionActivityDraft).filter(SessionActivityDraft.session_id == session_id).first()

    def get_by_id(self, db: Session, draft_id: int) -> SessionActivityDraft | None:
        return db.query(SessionActivityDraft).filter(SessionActivityDraft.id == draft_id).first()

    def upsert(
        self,
        db: Session,
        *,
        session_id: int,
        user_id: int,
        step: str,
        status: str,
        category_key: str | None = None,
        category_label: str | None = None,
        activity_key: str | None = None,
        activity_label: str | None = None,
        activity_date: date | None = None,
        activity_time: time | None = None,
        duration_minutes: int | None = None,
        source: str = "guided",
        raw_text: str | None = None,
        payload: dict | None = None,
    ) -> SessionActivityDraft:
        record = self.get_by_session_id(db=db, session_id=session_id)
        payload_json = json.dumps(payload or {}, ensure_ascii=True)
        if record:
            record.step = step
            record.status = status
            record.category_key = category_key
            record.category_label = category_label
            record.activity_key = activity_key
            record.activity_label = activity_label
            record.activity_date = activity_date
            record.activity_time = activity_time
            record.duration_minutes = duration_minutes
            record.source = source
            record.raw_text = raw_text
            record.payload_json = payload_json
        else:
            record = SessionActivityDraft(
                session_id=session_id,
                user_id=user_id,
                step=step,
                status=status,
                category_key=category_key,
                category_label=category_label,
                activity_key=activity_key,
                activity_label=activity_label,
                activity_date=activity_date,
                activity_time=activity_time,
                duration_minutes=duration_minutes,
                source=source,
                raw_text=raw_text,
                payload_json=payload_json,
            )
            db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def update_payload(self, db: Session, draft: SessionActivityDraft, payload: dict) -> SessionActivityDraft:
        draft.payload_json = json.dumps(payload or {}, ensure_ascii=True)
        db.commit()
        db.refresh(draft)
        return draft

    def clear(self, db: Session, session_id: int) -> None:
        record = self.get_by_session_id(db=db, session_id=session_id)
        if record:
            db.delete(record)
            db.commit()

    def clear_by_id(self, db: Session, draft_id: int) -> None:
        record = self.get_by_id(db=db, draft_id=draft_id)
        if record:
            db.delete(record)
            db.commit()
