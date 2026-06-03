from datetime import date, timedelta

from app.models.api_models import ActivityDecisionAction, ActivityDecisionResult
from app.services.activity_service import ActivityService


service = ActivityService()


def _analyze(message: str):
    return service.analyze_activity_message(message).model_dump()


def test_direct_water_logging_glasses():
    result = _analyze("I drank 2 glasses of water")
    action = result["actions"][0]
    assert action["entity"] == "water"
    assert action["action"] == "log"
    assert action["data"]["value"] == 500
    assert action["data"]["unit"] == "ml"


def test_direct_water_logging_liters():
    result = _analyze("Log 1.5 liters of water")
    action = result["actions"][0]
    assert action["data"]["value"] == 1500


def test_ambiguous_water_clarifies():
    result = _analyze("I had some water")
    assert result["actions"][0]["action"] == "clarify"
    assert result["actions"][0]["entity"] == "water"
    assert result["clarifications"]


def test_extreme_water_confirms():
    result = _analyze("I drank 12 liters of water")
    assert result["actions"][0]["action"] == "confirm"
    assert result["actions"][0]["entity"] == "water"


def test_direct_sleep_logging():
    result = _analyze("I slept 7 hours")
    action = result["actions"][0]
    assert action["entity"] == "sleep"
    assert action["action"] == "log"
    assert action["data"]["duration_minutes"] == 420


def test_sleep_range_logging():
    result = _analyze("I slept 4-5 hours")
    action = result["actions"][0]
    assert action["entity"] == "sleep"
    assert action["action"] == "log"
    assert action["data"]["value"] == 4.5
    assert "Approximate sleep range" in action["data"]["notes"]


def test_ambiguous_sleep_clarifies():
    result = _analyze("I slept badly")
    assert result["actions"][0]["entity"] == "sleep"
    assert result["actions"][0]["action"] == "clarify"


def test_extreme_sleep_confirms():
    result = _analyze("I slept 18 hours")
    assert result["actions"][0]["action"] == "confirm"


def test_weight_logging_kg():
    result = _analyze("My weight is 68 kg")
    action = result["actions"][0]
    assert action["entity"] == "weight"
    assert action["action"] == "log"
    assert action["data"]["value"] == 68
    assert action["data"]["unit"] == "kg"


def test_weight_logging_lb():
    result = _analyze("Weight 150 lb")
    action = result["actions"][0]
    assert action["data"]["value"] == 150
    assert action["data"]["unit"] == "lb"


def test_ambiguous_weight_clarifies():
    result = _analyze("log my weight")
    assert result["actions"][0]["entity"] == "weight"
    assert result["actions"][0]["action"] == "clarify"


def test_extreme_weight_confirms():
    result = _analyze("My weight is 5 kg")
    assert result["actions"][0]["entity"] == "weight"
    assert result["actions"][0]["action"] == "confirm"


def test_badminton_duration_logs():
    result = _analyze("I played badminton for 45 minutes")
    action = result["actions"][0]
    assert action["entity"] == "activity"
    assert action["action"] == "log"
    assert action["data"]["activity_name"] == "badminton"
    assert action["data"]["duration_minutes"] == 45


def test_soccer_normalizes_to_football():
    result = _analyze("I played soccer for 30 minutes")
    action = result["actions"][0]
    assert action["data"]["activity_name"] == "football"


def test_running_hours_converts_to_minutes():
    result = _analyze("I went for running for 1.5 hours")
    action = result["actions"][0]
    assert action["data"]["duration_minutes"] == 90


def test_worked_out_clarifies():
    result = _analyze("I worked out")
    assert result["actions"][0]["entity"] == "activity"
    assert result["actions"][0]["action"] == "clarify"


def test_mixed_sleep_and_mood():
    result = _analyze("I slept badly and feel stressed")
    entities = [action["entity"] for action in result["actions"]]
    assert "sleep" in entities
    assert "mood" in entities


def test_mixed_water_and_activity():
    result = _analyze("I drank 2 glasses of water and played badminton for 30 minutes")
    entities = [action["entity"] for action in result["actions"]]
    assert "water" in entities
    assert "activity" in entities


def test_multiple_logs_one_sentence():
    result = _analyze("I drank 2 glasses of water and slept 6 hours")
    entities = [action["entity"] for action in result["actions"]]
    assert "water" in entities
    assert "sleep" in entities


def test_sleep_correction_becomes_update():
    result = _analyze("No actually I slept 7 hours")
    assert result["actions"][0]["entity"] == "sleep"
    assert result["actions"][0]["action"] == "update"


def test_weight_correction_uses_latest_value():
    result = _analyze("not 70 kg, 68 kg")
    action = result["actions"][0]
    assert action["entity"] == "weight"
    assert action["action"] == "update"
    assert action["data"]["value"] == 68


def test_backdated_sleep_yesterday():
    result = _analyze("Yesterday I slept 7 hours")
    expected = (date.today() - timedelta(days=1)).isoformat()
    assert result["actions"][0]["data"]["logged_for_date"] == expected


def test_backdated_water_this_morning():
    result = _analyze("This morning I drank 2 glasses of water")
    action = result["actions"][0]
    assert action["data"]["time_context"] == "this morning"


def test_backdated_sleep_last_night():
    result = _analyze("Last night I slept 7 hours")
    expected = (date.today() - timedelta(days=1)).isoformat()
    assert result["actions"][0]["data"]["logged_for_date"] == expected
    assert result["actions"][0]["data"]["time_context"] == "night"


def test_backdated_weight_two_days_ago():
    result = _analyze("Two days ago my weight was 68 kg")
    expected = (date.today() - timedelta(days=2)).isoformat()
    assert result["actions"][0]["data"]["logged_for_date"] == expected


def test_parse_activity_text_backward_compatible():
    result = service.parse_activity_text("I played badminton for 60 minutes").model_dump()
    assert result["matched"] is True
    assert result["activity_name"] == "badminton"
    assert result["duration_minutes"] == 60


def test_missing_sleep_unit_clarifies():
    result = _analyze("sleep 7")
    assert result["actions"][0]["entity"] == "sleep"
    assert result["actions"][0]["action"] == "clarify"


def test_bare_number_does_not_guess_weight():
    result = _analyze("68")
    assert result["actions"][0]["action"] == "none"


def test_water_quantity_without_water_keyword_is_ignored():
    result = _analyze("2 glasses")
    assert result["actions"][0]["action"] == "none"


def test_activity_without_duration_clarifies():
    result = _analyze("I played football")
    assert result["actions"][0]["entity"] == "activity"
    assert result["actions"][0]["action"] == "clarify"


def test_duplicate_entity_actions_are_deduped():
    result = _analyze("I drank 2 glasses of water and 2 glasses of water")
    water_actions = [action for action in result["actions"] if action["entity"] == "water"]
    assert len(water_actions) == 1


def test_deterministic_output_for_same_input():
    one = _analyze("I slept 7 hours and feel calm")
    two = _analyze("I slept 7 hours and feel calm")
    assert one == two


def test_conversation_style_correction_updates():
    result = _analyze("Actually, I drank 3 glasses of water")
    assert result["actions"][0]["entity"] == "water"
    assert result["actions"][0]["action"] == "update"


def test_invalid_weight_extreme_confirm():
    result = _analyze("Weight 900 lb")
    assert result["actions"][0]["action"] == "confirm"


def test_activity_and_weight_same_sentence():
    result = _analyze("I played badminton for 40 minutes and my weight is 70 kg")
    entities = [action["entity"] for action in result["actions"]]
    assert "activity" in entities
    assert "weight" in entities


def test_water_and_mood_same_sentence():
    result = _analyze("I drank 500 ml water and feel happy")
    entities = [action["entity"] for action in result["actions"]]
    assert "water" in entities
    assert "mood" in entities


def test_no_activity_data_returns_none():
    result = _analyze("Can you tell me a joke?")
    assert result["actions"] == [{"entity": "activity", "action": "none", "data": {}}]


def test_contract_fields_always_present():
    result = _analyze("I slept 8 hours")
    assert set(result.keys()) == {"actions", "clarifications", "message"}


def test_confirm_action_adds_clarification():
    result = _analyze("I drank 11 liters of water")
    assert result["actions"][0]["action"] == "confirm"
    assert len(result["clarifications"]) == 1


def test_clarify_action_adds_clarification():
    result = _analyze("worked out")
    assert result["actions"][0]["action"] == "clarify"
    assert len(result["clarifications"]) == 1


def test_llm_candidate_is_validated_and_normalized(monkeypatch):
    monkeypatch.setattr(
        service,
        "_try_llm_extraction",
        lambda _message: ActivityDecisionResult(
            actions=[
                ActivityDecisionAction(
                    entity="sleep",
                    action="log",
                    data={"range_low": 4, "range_high": 5, "time_context": "last night"},
                )
            ],
            clarifications=[],
            message="candidate",
        ),
    )
    result = service.analyze_activity_message("I got around 4 or 5 hours last night").model_dump()
    action = result["actions"][0]
    assert action["entity"] == "sleep"
    assert action["action"] == "log"
    assert action["data"]["value"] == 4.5
    assert action["data"]["time_context"] == "night"


def test_llm_hallucinated_entity_falls_back_safely(monkeypatch):
    monkeypatch.setattr(
        service,
        "_try_llm_extraction",
        lambda _message: ActivityDecisionResult(
            actions=[ActivityDecisionAction(entity="weight", action="log", data={})],
            clarifications=[],
            message="candidate",
        ),
    )
    result = service.analyze_activity_message("Can you tell me a joke?").model_dump()
    assert result["actions"] == [{"entity": "activity", "action": "none", "data": {}}]
