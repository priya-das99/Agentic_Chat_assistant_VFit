from app.services.mood_service import MoodService


service = MoodService()


def test_quick_mood_options_are_available():
    options = service.get_quick_mood_options()
    labels = [option["label"] for option in options]
    assert labels == ["Ok", "Not good", "Pretty Good", "Awesome", "Horrible"]


def test_quick_mood_aliases_normalize_to_canonical_labels():
    cases = {
        "Ok": "neutral",
        "Not good": "sad",
        "Pretty Good": "happy",
        "Awesome": "great",
        "Horrible": "sad",
    }

    for raw_label, expected in cases.items():
        normalized, score = service.normalize_mood(raw_label)
        assert normalized == expected
        assert score is not None


def test_parse_mood_text_understands_quick_mood_phrases():
    result = service.parse_mood_text("I am feeling Pretty Good today")
    assert result.matched is True
    assert result.mood_label == "happy"

    result = service.parse_mood_text("I feel Not good because of work")
    assert result.matched is True
    assert result.mood_label == "sad"
    assert result.reason == "of work"

