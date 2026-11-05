from unittest.mock import MagicMock, patch

import pytest

from src.agent.voice.extraction import VoiceExtraction, extract_trip_details


def _extract(extraction):
    model = MagicMock()
    model.with_structured_output.return_value.invoke.return_value = extraction
    with patch("src.agent.voice.extraction.ChatAnthropic", return_value=model):
        return extract_trip_details("some speech")


def _data(**overrides):
    base = dict(
        destination="Lisbon", days=3, budget=900, trip_style="cultural",
        budget_stated=True, style_stated=True, preferences=None,
    )
    return VoiceExtraction(**{**base, **overrides})


def test_nothing_inferred_when_everything_was_stated():
    result = _extract(_data())
    assert result.inferred_fields == []
    assert result.preferences is None


def test_budget_and_style_flagged_when_not_stated():
    result = _extract(_data(budget_stated=False, style_stated=False))
    assert result.inferred_fields == ["budget", "trip_style"]


def test_blank_preferences_become_none():
    assert _extract(_data(preferences="   ")).preferences is None


def test_preferences_are_kept():
    assert _extract(_data(preferences="no museums")).preferences == "no museums"


def test_overlong_preferences_are_rejected():
    with pytest.raises(ValueError):
        _data(preferences="x" * 301)
