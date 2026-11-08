from src.evaluation.checks import VALID, evaluate_itinerary

TRIP = dict(destination="Rome", days=2, budget=800)


def _itinerary(**overrides):
    base = {
        "destination": "Rome, Italy",
        "total_days": 2,
        "estimated_total_cost": "$700",
        "days": [
            {"day": n, "theme": "Ancient Rome", "activities": [
                {"name": "Colosseum", "description": "Tour the arena", "estimated_cost": "$25"},
                {"name": "Forum walk", "description": "Free stroll", "estimated_cost": "Free"},
            ]}
            for n in (1, 2)
        ],
    }
    return {**base, **overrides}


def _failed(report):
    return {r.name for r in report.failures()}


def test_a_good_itinerary_passes_every_check():
    assert evaluate_itinerary(_itinerary(), **TRIP).passed


def test_invalid_structure_fails_fast_with_a_reason():
    report = evaluate_itinerary({"destination": "Rome"}, **TRIP)
    assert _failed(report) == {"matches_schema"}
    assert report.results[0].category == VALID


def test_wrong_number_of_days_fails_the_trip_match():
    report = evaluate_itinerary(_itinerary(total_days=1, days=_itinerary()["days"][:1]), **TRIP)
    assert "matches_trip" in _failed(report)


def test_wrong_destination_fails_relevance():
    report = evaluate_itinerary(_itinerary(destination="Madrid"), **TRIP)
    assert "matches_trip" in _failed(report)


def test_missing_description_fails_completeness():
    data = _itinerary()
    data["days"][0]["activities"][0]["description"] = "  "
    assert "activities_complete" in _failed(evaluate_itinerary(data, **TRIP))


def test_unparseable_cost_fails_format_but_free_is_fine():
    data = _itinerary()
    data["days"][0]["activities"][0]["estimated_cost"] = "a lot"
    assert "costs_parseable" in _failed(evaluate_itinerary(data, **TRIP))
    assert evaluate_itinerary(_itinerary(), **TRIP).passed


def test_wordy_but_valid_costs_are_accepted():
    data = _itinerary()
    data["days"][0]["activities"][0]["estimated_cost"] = "Free (optional donations)"
    data["days"][0]["activities"][1]["estimated_cost"] = "Included in activity cost"
    assert evaluate_itinerary(data, **TRIP).passed


def test_forbidden_content_is_caught_case_insensitively():
    data = _itinerary()
    data["days"][1]["activities"][0]["name"] = "Vatican Museum"
    report = evaluate_itinerary(data, must_not_mention=["museum"], **TRIP)
    assert "respects_exclusions" in _failed(report)
    assert "day 2" in next(r.detail for r in report.results if r.name == "respects_exclusions")
