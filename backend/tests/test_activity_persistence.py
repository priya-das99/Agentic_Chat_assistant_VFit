from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.db_models import ActivityLog, User
from app.services.activity_service import ActivityService


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


def test_apply_water_log_adds_to_same_day_total(db_session):
    service = ActivityService()

    first = service.analyze_activity_message("I drank 2 glasses of water")
    second = service.analyze_activity_message("I drank 1 glass of water")

    service.apply_activity_decision_result(db=db_session, user_id=1, decision=first)
    service.apply_activity_decision_result(db=db_session, user_id=1, decision=second)

    logs = db_session.query(ActivityLog).filter(ActivityLog.activity_name == "water").all()
    assert len(logs) == 1
    assert logs[0].value == 750
    assert service.get_total_value_for_day(db=db_session, user_id=1, activity_name="water") == 750


def test_apply_sleep_log_updates_same_day_record(db_session):
    service = ActivityService()

    first = service.analyze_activity_message("I slept 6 hours")
    second = service.analyze_activity_message("Actually I slept 7 hours")

    service.apply_activity_decision_result(db=db_session, user_id=1, decision=first)
    service.apply_activity_decision_result(db=db_session, user_id=1, decision=second)

    logs = db_session.query(ActivityLog).filter(ActivityLog.activity_name == "sleep").all()
    assert len(logs) == 1
    assert logs[0].value == 7
    assert logs[0].duration_minutes == 420


def test_apply_weight_log_updates_same_day_record(db_session):
    service = ActivityService()

    first = service.analyze_activity_message("My weight is 70 kg")
    second = service.analyze_activity_message("not 70 kg, 68 kg")

    service.apply_activity_decision_result(db=db_session, user_id=1, decision=first)
    service.apply_activity_decision_result(db=db_session, user_id=1, decision=second)

    logs = db_session.query(ActivityLog).filter(ActivityLog.activity_name == "weight").all()
    assert len(logs) == 1
    assert logs[0].value == 68
    assert logs[0].unit == "kg"


def test_apply_backdated_sleep_uses_backdated_created_at(db_session):
    service = ActivityService()
    decision = service.analyze_activity_message("Yesterday I slept 7 hours")

    service.apply_activity_decision_result(db=db_session, user_id=1, decision=decision)

    log = db_session.query(ActivityLog).filter(ActivityLog.activity_name == "sleep").one()
    assert log.created_at.date() == date.today() - timedelta(days=1)


def test_apply_backdated_activity_uses_time_context(db_session):
    service = ActivityService()
    decision = service.analyze_activity_message("This morning I played badminton for 30 minutes")

    service.apply_activity_decision_result(db=db_session, user_id=1, decision=decision)

    log = db_session.query(ActivityLog).filter(ActivityLog.activity_name == "badminton").one()
    assert log.created_at.hour == 9


def test_apply_skips_non_mutating_actions(db_session):
    service = ActivityService()
    decision = service.analyze_activity_message("I slept badly and feel stressed")

    result = service.apply_activity_decision_result(db=db_session, user_id=1, decision=decision)

    assert result["applied"] == []
    assert len(result["skipped"]) == 2
    assert db_session.query(ActivityLog).count() == 0
