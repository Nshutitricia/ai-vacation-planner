from langchain_core.tools import tool

from src.llm.tools import WeatherTool

_weather_tool = WeatherTool()


@tool(description=(
    "Get current weather conditions for a city, to help plan "
    "weather-appropriate activities for a trip."
))
def get_weather(city: str) -> str:
    return _weather_tool.get_weather(city)
