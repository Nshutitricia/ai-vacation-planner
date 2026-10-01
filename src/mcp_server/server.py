
from mcp.server.fastmcp import FastMCP

from src.agent.tools.maps import _fetch_place
from src.agent.tools.weather import _fetch_weather

mcp = FastMCP("vacation-planner-tools")


@mcp.tool(description=(
    "Get current weather conditions for a city, to help plan "
    "weather-appropriate activities for a trip."
))
def get_weather(city: str) -> str:
    return _fetch_weather(city)


@mcp.tool(description=(
    "Look up a place — a landmark, address, neighborhood, or business — "
    "and return its location details (name and coordinates), to help "
    "plan routes and confirm a place actually exists near the "
    "destination."
))
def find_place(query: str) -> str:
    return _fetch_place(query)


if __name__ == "__main__":
    mcp.run(transport="stdio")
