from sqlalchemy.orm import Session

from app.models.db_models import SessionSummary


class SessionSummaryRepository:
    def get_by_session_id(self, db: Session, session_id: int) -> SessionSummary | None:
        return db.query(SessionSummary).filter(SessionSummary.session_id == session_id).first()

    def upsert_summary(self, db: Session, session_id: int, user_id: int, summary_text: str) -> SessionSummary:
        record = self.get_by_session_id(db=db, session_id=session_id)
        if record:
            record.summary_text = summary_text
        else:
            record = SessionSummary(session_id=session_id, user_id=user_id, summary_text=summary_text)
            db.add(record)

        db.commit()
        db.refresh(record)
        return record
