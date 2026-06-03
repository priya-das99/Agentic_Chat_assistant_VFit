import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.db_models import ActivityLog, SessionActivityDecisionState, User
from app.services.chat_service import ChatService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    session.add(User(id=1, name="Test User"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


def test_chat_service_logs_activity_directly(db_session, monkeypatch):
    chat_service = ChatService()
    monkeypatch.setattr("app.services.chat_service.run_main_agent", lambda **kwargs: pytest.fail("run_main_agent should not be called for direct activity logs"))

    reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="I drank 2 glasses of water"))

    assert "Logged" in reply
    assert "water" in reply
    assert db_session.query(ActivityLog).filter(ActivityLog.activity_name == "water").count() == 1
    assert db_session.query(SessionActivityDecisionState).count() == 0


def test_chat_service_handles_confirm_followup(db_session, monkeypatch):
    chat_service = ChatService()
    monkeypatch.setattr("app.services.chat_service.run_main_agent", lambda **kwargs: pytest.fail("run_main_agent should not be called for activity follow-ups"))

    first_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="I drank 12 liters of water"))
    second_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="yes"))

    assert "log it anyway" in first_reply.lower()
    assert "water" in second_reply.lower()
    assert db_session.query(ActivityLog).filter(ActivityLog.activity_name == "water").count() == 1
    assert db_session.query(SessionActivityDecisionState).count() == 0


def test_chat_service_handles_clarify_followup(db_session, monkeypatch):
    chat_service = ChatService()
    monkeypatch.setattr("app.services.chat_service.run_main_agent", lambda **kwargs: pytest.fail("run_main_agent should not be called for activity follow-ups"))

    first_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="I slept badly"))
    second_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="7"))

    assert "how many hours" in first_reply.lower()
    assert "sleep" in second_reply.lower()
    assert db_session.query(ActivityLog).filter(ActivityLog.activity_name == "sleep").count() == 1
    assert db_session.query(SessionActivityDecisionState).count() == 0
