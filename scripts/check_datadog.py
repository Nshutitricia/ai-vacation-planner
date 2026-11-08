"""Check the Datadog settings in .env without printing the key.

    python scripts/check_datadog.py

Tells you whether the key looks like an API key and whether Datadog accepts it
for the configured site.
"""
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings


def describe_key(key: str) -> str:
    if not key:
        return "EMPTY - DD_API_KEY is not being read from .env"
    if key != key.strip() or key[0] in "'\"" or key[-1] in "'\"":
        return "has spaces or quotes around it - remove them"
    if re.fullmatch(r"[0-9a-f]{32}", key):
        return "32 hex characters - the right shape for an API key"
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", key):
        return "looks like a key ID (a UUID) - you need the key VALUE instead"
    if len(key) == 40:
        return "40 characters - looks like an APPLICATION key, not an API key"
    return f"{len(key)} characters - unexpected shape for an API key (expected 32 hex characters)"


def validate(key: str, site: str) -> str:
    request = urllib.request.Request(
        f"https://api.{site}/api/v1/validate", headers={"DD-API-KEY": key}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return f"Datadog accepted the key (HTTP {response.status})"
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return "Datadog REJECTED the key (HTTP 403) - wrong key, or created on a different Datadog site"
        return f"Datadog answered HTTP {e.code}"
    except Exception as e:
        return f"Could not reach Datadog: {type(e).__name__}"


if __name__ == "__main__":
    print(f"DATADOG_ENABLED : {settings.DATADOG_ENABLED}")
    print(f"DD_SITE         : {settings.DD_SITE}")
    print(f"DD_API_KEY      : {describe_key(settings.DD_API_KEY)}")
    if settings.DD_API_KEY:
        print(f"Validation      : {validate(settings.DD_API_KEY, settings.DD_SITE)}")
