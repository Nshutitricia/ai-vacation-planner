import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class WeatherTool:
    """
    Tool for getting current weather data.
    Uses wttr.in free weather API - no API key needed.
    Separation of concern: only handles weather lookup.
    """

    name = "get_weather"
    description = "Get the current weather for a destination city"

    # this is what we send to Claude to describe the tool
    definition = {
        "name": "get_weather",
        "description": "Get current weather conditions for a city to help plan appropriate activities",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name to get weather for e.g. Paris, London, Kigali"
                }
            },
            "required": ["city"]
        }
    }

    def get_weather(self, city: str) -> str:
        """
        Fetch current weather for a city from wttr.in.
        Returns a human readable weather string.
        Falls back to a default message if the API fails.
        """
        try:
            city_url = city.replace(" ", "+").replace(",", "")
            url = f"https://wttr.in/{city_url}?format=j1"
            logger.info(f"Fetching weather for {city} from wttr.in")

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "VacationPlanner/1.0"}
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())

            current = data["current_condition"][0]

            temp_c = current["temp_C"]
            feels_like = current["FeelsLikeC"]
            description = current["weatherDesc"][0]["value"]
            humidity = current["humidity"]
            wind_speed = current["windspeedKmph"]

            weather_str = (
                f"{description}, {temp_c}°C "
                f"(feels like {feels_like}°C), "
                f"humidity {humidity}%, "
                f"wind {wind_speed} km/h"
            )

            logger.info(f"Weather for {city}: {weather_str}")
            return weather_str

        except urllib.error.URLError as e:
            logger.warning(f"Could not fetch weather for {city}: {str(e)}")
            return self._fallback_weather(city)
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Could not parse weather for {city}: {str(e)}")
            return self._fallback_weather(city)
        except Exception as e:
            logger.warning(f"Unexpected error getting weather for {city}: {str(e)}")
            return self._fallback_weather(city)

    def _fallback_weather(self, city: str) -> str:
        """
        Return a fallback message when weather API fails.
        This ensures itinerary generation continues even without weather data.
        """
        logger.info(f"Using fallback weather for {city}")
        return f"Weather data unavailable for {city}. Plan for varied conditions."

    def process_tool_call(self, tool_input: dict) -> str:
        """
        Process a tool call from Claude.
        Called when Claude requests weather data.
        """
        city = tool_input.get("city", "")
        if not city:
            return "No city provided"
        return self.get_weather(city)