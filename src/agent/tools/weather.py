from langchain_core.tools import tool

from src.llm.tools import WeatherTool

_weather_tool = WeatherTool()


@tool
def get_weather(city: str) -> str:

    return _weather_tool.get_weather(city)
