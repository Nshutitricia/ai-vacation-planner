import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from src.mcp_server.errors import ProviderUnavailableError

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def fetch_place(query: str) -> str:
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
        raise ProviderUnavailableError(
            f"Location lookup is unavailable for '{query}'."
        ) from e
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.warning(f"Could not parse place lookup for '{query}': {str(e)}")
        raise ProviderUnavailableError(
            f"Location lookup returned unusable data for '{query}'."
        ) from e
    except OSError as e:
        logger.warning(f"Network error looking up place '{query}': {str(e)}")
        raise ProviderUnavailableError(
            f"Location lookup is unavailable for '{query}'."
        ) from e
