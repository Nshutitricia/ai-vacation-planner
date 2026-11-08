"""The assignment asks for the API to be documented via Swagger (OpenAPI)."""
import pytest

EXPECTED_ROUTES = [
    ("post", "/auth/register"),
    ("post", "/auth/login"),
    ("get", "/users/me"),
    ("post", "/trips"),
    ("get", "/trips"),
    ("get", "/trips/{trip_id}"),
    ("put", "/trips/{trip_id}"),
    ("delete", "/trips/{trip_id}"),
    ("post", "/itinerary/generate"),
    ("get", "/itinerary/{trip_id}"),
    ("get", "/itinerary/{trip_id}/audio"),
    ("get", "/knowledge/search"),
    ("post", "/voice/plan"),
]


@pytest.fixture
def spec(client):
    return client.get("/openapi.json").json()


@pytest.mark.parametrize("method,path", EXPECTED_ROUTES)
def test_every_route_is_documented(spec, method, path):
    assert method in spec["paths"][path]


def test_swagger_ui_is_served(client):
    assert client.get("/docs").status_code == 200


def test_audio_endpoint_is_documented_as_mp3_not_json(spec):
    content = spec["paths"]["/itinerary/{trip_id}/audio"]["get"]["responses"]["200"]["content"]
    assert "audio/mpeg" in content


def test_voice_response_documents_the_assumptions_it_reports(spec):
    properties = spec["components"]["schemas"]["VoicePlanResponse"]["properties"]
    assert {"trip_details", "preferences", "inferred_fields"} <= set(properties)


@pytest.mark.parametrize("method,path,codes", [
    ("post", "/trips", {"401", "422"}),
    ("post", "/itinerary/generate", {"400", "401", "403", "404", "500"}),
    ("post", "/voice/plan", {"400", "401", "500"}),
    ("get", "/itinerary/{trip_id}/audio", {"401", "403", "404", "500"}),
])
def test_error_responses_are_documented(spec, method, path, codes):
    assert codes <= set(spec["paths"][path][method]["responses"])


@pytest.mark.parametrize("method,path", [
    ("post", "/trips"), ("post", "/itinerary/generate"), ("post", "/voice/plan"),
])
def test_endpoints_explain_what_they_do(spec, method, path):
    assert spec["paths"][path][method].get("description")
