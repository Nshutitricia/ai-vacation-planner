from types import SimpleNamespace

from src.agent.graph import _allowed_only


def test_unexpected_mcp_tools_are_dropped():
    tools = [SimpleNamespace(name=n) for n in
             ("get_weather", "find_place", "send_email", "delete_trip")]
    assert [t.name for t in _allowed_only(tools)] == ["get_weather", "find_place"]
