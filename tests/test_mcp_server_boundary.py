import asyncio
import urllib.error
from unittest.mock import patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from src.mcp_server.server import mcp


def _call(name, args):
    return asyncio.run(mcp.call_tool(name, args))


def test_provider_failure_becomes_an_mcp_tool_error():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        with pytest.raises(ToolError, match="unavailable"):
            _call("get_weather", {"city": "Paris"})


def test_place_provider_failure_becomes_an_mcp_tool_error():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        with pytest.raises(ToolError):
            _call("find_place", {"query": "eiffel"})
