import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from src.mcp_server.errors import ProviderUnavailableError
from src.mcp_server.maps import fetch_place
from src.mcp_server.weather import fetch_weather


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _respond(payload):
    return FakeResponse(json.dumps(payload).encode())


WEATHER_OK = {
    "current_condition": [{
        "temp_C": "20", "FeelsLikeC": "19", "humidity": "50",
        "windspeedKmph": "10", "weatherDesc": [{"value": "Sunny"}],
    }]
}


def test_weather_success():
    with patch("urllib.request.urlopen", return_value=_respond(WEATHER_OK)):
        assert "Sunny, 20" in fetch_weather("Paris")


def test_weather_network_failure_raises():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        with pytest.raises(ProviderUnavailableError):
            fetch_weather("Paris")


def test_weather_timeout_raises():
    with patch("urllib.request.urlopen", side_effect=TimeoutError("slow")):
        with pytest.raises(ProviderUnavailableError):
            fetch_weather("Paris")


def test_weather_bad_payload_raises():
    with patch("urllib.request.urlopen", return_value=_respond({"nope": 1})):
        with pytest.raises(ProviderUnavailableError):
            fetch_weather("Paris")


def test_place_success():
    data = [{"display_name": "Eiffel Tower", "lat": "48.8", "lon": "2.3"}]
    with patch("urllib.request.urlopen", return_value=_respond(data)):
        assert "Eiffel Tower" in fetch_place("eiffel")


def test_place_no_match_is_a_normal_result():
    with patch("urllib.request.urlopen", return_value=_respond([])):
        assert fetch_place("zzzz") == "No location found for 'zzzz'."


def test_place_network_failure_raises():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        with pytest.raises(ProviderUnavailableError):
            fetch_place("eiffel")


def test_place_bad_payload_raises():
    with patch("urllib.request.urlopen", return_value=_respond([{"oops": 1}])):
        with pytest.raises(ProviderUnavailableError):
            fetch_place("eiffel")
