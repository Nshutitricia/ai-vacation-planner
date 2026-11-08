from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph

from src.agent.graph import build_tool_node


@tool(description="Always fails, like a provider that is down or rate limited.")
def flaky_search(query: str) -> str:
    raise RuntimeError("RateLimitError: you have reduced rate limits of 3 RPM")


@tool(description="Always works.")
def steady_lookup(query: str) -> str:
    return "ok"


def _run_tools(tools, calls):
    """Run a ToolNode inside a one-step graph, the way the agent uses it."""
    graph = StateGraph(MessagesState)
    graph.add_node("tools", build_tool_node(tools))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    state = graph.compile().invoke({"messages": [AIMessage(content="", tool_calls=calls)]})
    return state["messages"][1:]  # drop the AI message that made the calls


def _call(name, call_id):
    return {"name": name, "args": {"query": "rome"}, "id": call_id}


def test_a_failing_tool_is_reported_to_the_model_instead_of_crashing():
    message = _run_tools([flaky_search], [_call("flaky_search", "1")])[0]
    assert message.status == "error"
    assert "unavailable" in message.content
    assert "RPM" not in message.content  # provider details are logged, not sent to the model


def test_one_failing_tool_does_not_stop_the_others_in_the_same_step():
    calls = [_call("flaky_search", "1"), _call("steady_lookup", "2")]
    by_id = {m.tool_call_id: m for m in _run_tools([flaky_search, steady_lookup], calls)}
    assert by_id["1"].status == "error"
    assert by_id["2"].content == "ok"
