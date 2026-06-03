from sqlalchemy.orm import Session

from app.models.db_models import SessionShortcutState


class SessionShortcutStateRepository:
    def get_by_session_id(self, db: Session, session_id: int) -> SessionShortcutState | None:
        return db.query(SessionShortcutState).filter(SessionShortcutState.session_id == session_id).first()

    def upsert_pending_action(self, db: Session, session_id: int, user_id: int, pending_action: str) -> SessionShortcutState:
        record = self.get_by_session_id(db=db, session_id=session_id)
        if record:
            record.pending_action = pending_action
        else:
            record = SessionShortcutState(session_id=session_id, user_id=user_id, pending_action=pending_action)
            db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def clear_pending_action(self, db: Session, session_id: int) -> None:
        record = self.get_by_session_id(db=db, session_id=session_id)
        if record:
            db.delete(record)
            db.commit()
