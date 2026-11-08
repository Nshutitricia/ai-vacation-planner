from unittest.mock import patch

import pytest

from src.observability.usage import current_tracker

from tests.api.conftest import make_itinerary

AGENT = "src.services.itinerary_service.run_agent"


def _generate(client, headers, trip_id):
    return client.post("/itinerary/generate", json={"trip_id": trip_id}, headers=headers)


def test_generate_returns_and_saves_an_itinerary(client, alice, trip_id):
    with patch(AGENT, return_value=make_itinerary()):
        response = _generate(client, alice, trip_id)
    assert response.status_code == 201
    body = response.json()
    assert body["trip_id"] == trip_id and len(body["days"]) == 3
    assert "generated" in body["message"]
    assert client.get(f"/itinerary/{trip_id}", headers=alice).json()["days"] == body["days"]


def test_the_trip_details_reach_the_agent(client, alice, trip_id):
    with patch(AGENT, return_value=make_itinerary()) as agent:
        _generate(client, alice, trip_id)
    request = agent.call_args.args[0]
    assert "Lisbon" in request and "<trip_details>" in request


def test_generating_twice_is_rejected(client, alice, trip_id):
    with patch(AGENT, return_value=make_itinerary()):
        _generate(client, alice, trip_id)
        second = _generate(client, alice, trip_id)
    assert second.status_code == 400 and "already exists" in second.json()["detail"]


def test_a_bad_plan_is_regenerated_once_and_the_good_one_is_saved(client, alice, trip_id):
    with patch(AGENT, side_effect=[make_itinerary(destination="Madrid"), make_itinerary()]) as agent:
        response = _generate(client, alice, trip_id)
    assert response.status_code == 201 and agent.call_count == 2


def test_a_plan_that_keeps_failing_validation_is_never_saved(client, alice, trip_id):
    with patch(AGENT, side_effect=[make_itinerary(days=2)] * 2):
        response = _generate(client, alice, trip_id)
    assert response.status_code == 500
    assert response.json()["detail"] == "AI generation failed. Please try again later."
    assert client.get(f"/itinerary/{trip_id}", headers=alice).status_code == 404


def test_agent_errors_do_not_leak_details(client, alice, trip_id):
    with patch(AGENT, side_effect=RuntimeError("secret internal detail")):
        response = _generate(client, alice, trip_id)
    assert response.status_code == 500
    assert "secret" not in response.text


def test_other_users_cannot_generate_for_my_trip(client, alice, bob, trip_id):
    with patch(AGENT, return_value=make_itinerary()) as agent:
        assert _generate(client, bob, trip_id).status_code == 403
    agent.assert_not_called()


def test_generate_requires_login_and_a_real_trip(client, alice):
    assert client.post("/itinerary/generate", json={"trip_id": 1}).status_code == 401
    assert _generate(client, alice, 9999).status_code == 404
    assert client.post("/itinerary/generate", json={"trip_id": 0}, headers=alice).status_code == 422


def test_get_itinerary_is_404_until_one_exists(client, alice, trip_id):
    assert client.get(f"/itinerary/{trip_id}", headers=alice).status_code == 404


def test_audio_returns_mp3_bytes(client, alice, trip_id):
    with patch(AGENT, return_value=make_itinerary()):
        _generate(client, alice, trip_id)
    with patch("src.services.itinerary_service.narrate_itinerary", return_value="A short story."), \
         patch("src.routers.itinerary.synthesize_speech", return_value=b"ID3-fake-mp3") as speech:
        response = client.get(f"/itinerary/{trip_id}/audio", headers=alice)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"ID3-fake-mp3"
    speech.assert_called_once_with("A short story.")


def test_audio_falls_back_to_the_plain_summary_when_narration_fails(client, alice, trip_id):
    with patch(AGENT, return_value=make_itinerary()):
        _generate(client, alice, trip_id)
    with patch("src.services.itinerary_service.narrate_itinerary", side_effect=ValueError("claude down")), \
         patch("src.routers.itinerary.synthesize_speech", return_value=b"mp3") as speech:
        response = client.get(f"/itinerary/{trip_id}/audio", headers=alice)
    assert response.status_code == 200
    assert "Day 1" in speech.call_args.args[0]


def test_audio_needs_an_itinerary_and_the_owner(client, alice, bob, trip_id):
    assert client.get(f"/itinerary/{trip_id}/audio", headers=alice).status_code == 404
    assert client.get(f"/itinerary/{trip_id}/audio", headers=bob).status_code == 403


def _agent_that_uses_tokens(fail=False):
    def agent(request, session):
        current_tracker().record(1000, 200, "claude-haiku-4-5-20251001")
        if fail:
            raise RuntimeError("claude down")
        return make_itinerary()

    return agent


def test_token_usage_and_cost_are_reported_for_a_generation(client, alice, trip_id):
    with patch(AGENT, side_effect=_agent_that_uses_tokens()), \
         patch("src.observability.datadog.annotate") as annotate:
        assert _generate(client, alice, trip_id).status_code == 201
    metrics = annotate.call_args.kwargs["metrics"]
    assert metrics["total_tokens"] == 1200
    assert metrics["total_cost"] == pytest.approx(0.002)


def test_usage_is_still_reported_when_generation_fails(client, alice, trip_id):
    with patch(AGENT, side_effect=_agent_that_uses_tokens(fail=True)), \
         patch("src.observability.datadog.annotate") as annotate:
        assert _generate(client, alice, trip_id).status_code == 500
    assert annotate.call_args.kwargs["metrics"]["total_tokens"] == 1200
