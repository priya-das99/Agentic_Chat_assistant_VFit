import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.db_models import ActivityLog, ChatSession, User
from app.services.activity_flow_service import ActivityFlowService
from app.services.chat_service import ChatService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    session.add(User(id=1, name="Test User"))
    session.add(ChatSession(id=1, user_id=1, status="active"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


def test_catalog_groups_are_seeded(db_session):
    service = ActivityFlowService()
    catalog = service.get_catalog(db_session)

    category_keys = [group.category_key for group in catalog]
    assert "well_being" in category_keys
    assert "most_popular" in category_keys
    assert "cardio_vascular" in category_keys
    assert "sports" in category_keys


def test_guided_flow_progresses_through_date_duration_time(db_session):
    service = ActivityFlowService()

    draft = service.start_flow(db_session, session_id=1, user_id=1, category_key="sports", activity_key="badminton")
    assert draft.step == "date"
    assert "When did you do" in draft.prompt

    after_date = service.update_flow(db_session, session_id=1, user_id=1, activity_date="yesterday")
    assert after_date.step == "duration"
    assert "How long" in after_date.prompt

    after_duration = service.update_flow(db_session, session_id=1, user_id=1, duration_minutes=20)
    assert after_duration.step == "time"
    assert "What time" in after_duration.prompt

    after_time = service.update_flow(db_session, session_id=1, user_id=1, activity_time="18:00")
    assert after_time.log_result is not None
    assert db_session.query(ActivityLog).filter(ActivityLog.activity_name == "badminton").count() == 1


def test_manual_text_starts_guided_activity_flow_in_chat(db_session, monkeypatch):
    chat_service = ChatService()
    monkeypatch.setattr("app.services.chat_service.run_main_agent", lambda **kwargs: pytest.fail("run_main_agent should not be called for guided activity flow"))

    first_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="I played badminton for 20 mins"))
    second_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="yesterday"))
    third_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="20 minutes"))
    fourth_reply = asyncio.run(chat_service.process_message(db=db_session, user_id=1, message="6 pm"))

    assert "when did you do badminton" in first_reply.lower()
    assert "how long" in second_reply.lower() or "how long" in third_reply.lower()
    assert "time" in fourth_reply.lower() or "logged" in fourth_reply.lower()
    assert db_session.query(ActivityLog).filter(ActivityLog.activity_name == "badminton").count() == 1
