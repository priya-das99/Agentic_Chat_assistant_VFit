import json

from sqlalchemy.orm import Session

from app.models.db_models import SessionMoodDraft


class MoodDraftRepository:
    def get_by_session_id(self, db: Session, session_id: int) -> SessionMoodDraft | None:
        return db.query(SessionMoodDraft).filter(SessionMoodDraft.session_id == session_id).first()

    def get_by_id(self, db: Session, draft_id: int) -> SessionMoodDraft | None:
        return db.query(SessionMoodDraft).filter(SessionMoodDraft.id == draft_id).first()

    def upsert(
        self,
        db: Session,
        *,
        session_id: int,
        user_id: int,
        step: str,
        status: str,
        mood_label: str,
        mood_score: int | None = None,
        emoji: str | None = None,
        raw_text: str | None = None,
        payload: dict | None = None,
    ) -> SessionMoodDraft:
        record = self.get_by_session_id(db=db, session_id=session_id)
        payload_json = json.dumps(payload or {}, ensure_ascii=True)
        if record:
            record.step = step
            record.status = status
            record.mood_label = mood_label
            record.mood_score = mood_score
            record.emoji = emoji
            record.raw_text = raw_text
            record.payload_json = payload_json
        else:
            record = SessionMoodDraft(
                session_id=session_id,
                user_id=user_id,
                step=step,
                status=status,
                mood_label=mood_label,
                mood_score=mood_score,
                emoji=emoji,
                raw_text=raw_text,
                payload_json=payload_json,
            )
            db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def update_payload(self, db: Session, draft: SessionMoodDraft, payload: dict) -> SessionMoodDraft:
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
