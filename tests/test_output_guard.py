from unittest.mock import patch

import pytest

from src.guardrails.errors import OutputGuardError
from src.guardrails.output_guard import find_problems, validate_itinerary
from src.models.trip import Trip
from src.schemas.itinerary_schema import ItinerarySchema
from src.services.itinerary_service import ItineraryService


def _trip(**overrides):
    base = dict(id=1, destination="Lisbon", days=2, budget=1000, trip_style="cultural", user_id=1)
    return Trip(**{**base, **overrides})


def _itinerary(destination="Lisbon, Portugal", days=2, cost="$900", numbers=None):
    numbers = numbers or list(range(1, days + 1))
    return ItinerarySchema.model_validate({
        "destination": destination,
        "total_days": days,
        "estimated_total_cost": cost,
        "days": [
            {"day": n, "theme": "T", "activities": [
                {"name": "Walk", "description": "Stroll", "estimated_cost": "$0"}]}
            for n in numbers
        ],
    })


def test_a_good_itinerary_passes():
    assert find_problems(_itinerary(), _trip()) == []
    validate_itinerary(_itinerary(), _trip())


def test_wrong_destination_is_caught():
    assert any("destination" in p for p in find_problems(_itinerary(destination="Madrid"), _trip()))


def test_wrong_number_of_days_is_caught():
    assert any("expected 2 day" in p for p in find_problems(_itinerary(days=3), _trip()))


def test_out_of_order_day_numbers_are_caught():
    problems = find_problems(_itinerary(numbers=[2, 1]), _trip())
    assert any("day numbers" in p for p in problems)


def test_wildly_over_budget_is_caught_but_modestly_over_is_not():
    assert any("budget" in p for p in find_problems(_itinerary(cost="$5,000"), _trip()))
    assert find_problems(_itinerary(cost="$1,400"), _trip()) == []


def test_unparseable_cost_is_not_treated_as_a_failure():
    assert find_problems(_itinerary(cost="varies"), _trip()) == []


def test_validate_raises_with_every_problem():
    with pytest.raises(OutputGuardError) as err:
        validate_itinerary(_itinerary(destination="Madrid", days=3), _trip())
    assert "destination" in str(err.value) and "expected 2 day" in str(err.value)


# --- service behaviour: regenerate once, then fail --------------------------

def test_a_bad_first_attempt_is_regenerated():
    with patch("src.services.itinerary_service.run_agent",
               side_effect=[_itinerary(destination="Madrid"), _itinerary()]) as agent:
        result = ItineraryService()._run_validated_agent("req", _trip(), None)
    assert agent.call_count == 2
    assert result.destination == "Lisbon, Portugal"


def test_two_bad_attempts_raise_instead_of_returning_a_bad_plan():
    with patch("src.services.itinerary_service.run_agent",
               side_effect=[_itinerary(destination="Madrid")] * 2) as agent:
        with pytest.raises(OutputGuardError):
            ItineraryService()._run_validated_agent("req", _trip(), None)
    assert agent.call_count == 2
