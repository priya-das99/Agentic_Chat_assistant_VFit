from sqlalchemy.orm import Session

from app.models.db_models import SessionActivityDecisionState


class SessionActivityDecisionRepository:
    def get_by_session_id(self, db: Session, session_id: int) -> SessionActivityDecisionState | None:
        return db.query(SessionActivityDecisionState).filter(SessionActivityDecisionState.session_id == session_id).first()

    def upsert(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        pending_type: str,
        decision_payload: str,
        prompt_text: str,
    ) -> SessionActivityDecisionState:
        record = self.get_by_session_id(db=db, session_id=session_id)
        if record:
            record.pending_type = pending_type
            record.decision_payload = decision_payload
            record.prompt_text = prompt_text
        else:
            record = SessionActivityDecisionState(
                session_id=session_id,
                user_id=user_id,
                pending_type=pending_type,
                decision_payload=decision_payload,
                prompt_text=prompt_text,
            )
            db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def clear(self, db: Session, session_id: int) -> None:
        record = self.get_by_session_id(db=db, session_id=session_id)
        if record:
            db.delete(record)
            db.commit()
