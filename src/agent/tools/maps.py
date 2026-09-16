import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@tool(description=(
    "Look up a place — a landmark, address, neighborhood, or business — "
    "and return its location details (name and coordinates), to help "
    "plan routes and confirm a place actually exists near the "
    "destination."
))
def find_place(query: str) -> str:
    try:
        params = urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "limit": 3,
        })
        url = f"{NOMINATIM_URL}?{params}"
        logger.info(f"Looking up place: {query}")

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "VacationPlanner/1.0"}
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            results = json.loads(response.read().decode())

        if not results:
            return f"No location found for '{query}'."

        formatted = [
            f"{r['display_name']} (lat: {r['lat']}, lon: {r['lon']})"
            for r in results
        ]
        return "\n".join(formatted)

    except urllib.error.URLError as e:
        logger.warning(f"Could not look up place '{query}': {str(e)}")
        return f"Location lookup for '{query}' is currently unavailable."
    except (KeyError, json.JSONDecodeError) as e:
        logger.warning(f"Could not parse place lookup for '{query}': {str(e)}")
        return f"Location lookup for '{query}' is currently unavailable."
    except Exception as e:
        logger.warning(f"Unexpected error looking up place '{query}': {str(e)}")
        return f"Location lookup for '{query}' is currently unavailable."
