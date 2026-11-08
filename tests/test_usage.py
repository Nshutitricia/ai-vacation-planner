from unittest.mock import patch
from uuid import uuid4

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from langgraph.graph import END, START, MessagesState, StateGraph

from src.observability import datadog
from src.observability.usage import (
    UsageTracker,
    current_tracker,
    price_for,
    report_usage,
    track_usage,
)

HAIKU = "claude-haiku-4-5-20251001"


def _reply(input_tokens, output_tokens, model=HAIKU):
    return AIMessage(
        content="ok",
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
        response_metadata={"model_name": model},
    )


def test_tracker_adds_up_tokens_from_every_call():
    tracker = UsageTracker()
    for message in (_reply(100, 20), _reply(300, 50)):
        tracker.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]))
    assert (tracker.input_tokens, tracker.output_tokens, tracker.calls) == (400, 70, 2)
    assert tracker.total_tokens == 470
    assert tracker.model == HAIKU


def test_a_response_without_usage_is_ignored():
    tracker = UsageTracker()
    tracker.on_llm_end(LLMResult(generations=[[ChatGeneration(message=AIMessage(content="no usage"))]]))
    assert tracker.calls == 0


def test_cost_is_calculated_from_the_price_table():
    tracker = UsageTracker()
    tracker.record(1_000_000, 1_000_000, HAIKU)
    costs = tracker.costs()
    assert costs["input_cost"] == pytest.approx(1.00)
    assert costs["output_cost"] == pytest.approx(5.00)
    assert costs["total_cost"] == pytest.approx(6.00)
    assert tracker.as_dict()["estimated_cost_usd"] == 6.0


def test_dated_model_names_match_their_base_price():
    assert price_for("claude-haiku-4-5-20251001") == price_for("claude-haiku-4-5")


def test_an_unknown_model_gets_tokens_but_no_invented_cost():
    tracker = UsageTracker()
    tracker.record(500, 100, "some-future-model")
    assert tracker.total_tokens == 600
    assert tracker.costs() is None
    assert tracker.as_dict()["estimated_cost_usd"] is None


def test_tokens_are_counted_through_langgraph_without_passing_the_tracker_to_the_model():
    """The agent's nodes call the model without a config; callbacks still have to reach it."""
    model = FakeMessagesListChatModel(responses=[_reply(120, 30), _reply(80, 20)])

    def agent(state):
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("first", agent)
    graph.add_node("second", agent)
    graph.add_edge(START, "first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)

    tracker = UsageTracker()
    graph.compile().invoke({"messages": [("user", "plan a trip")]}, config={"callbacks": [tracker]})
    assert (tracker.input_tokens, tracker.output_tokens, tracker.calls) == (200, 50, 2)


def test_track_usage_is_scoped_to_its_block():
    assert current_tracker() is None
    with track_usage() as tracker:
        assert current_tracker() is tracker
    assert current_tracker() is None


def test_reporting_attaches_the_usage_summary_to_the_datadog_span():
    tracker = UsageTracker()
    tracker.record(1000, 200, HAIKU)
    with patch("src.observability.datadog.annotate") as annotate:
        report_usage(tracker, "trip 1")
    usage = annotate.call_args.kwargs["metadata"]["usage"]
    assert usage["model"] == HAIKU
    assert usage["total_tokens"] == 1200
    assert usage["estimated_cost_usd"] == pytest.approx(0.002)
    assert "metrics" not in annotate.call_args.kwargs


def test_nothing_is_reported_when_no_model_was_called():
    with patch("src.observability.datadog.annotate") as annotate:
        report_usage(UsageTracker(), "trip 1")
    annotate.assert_not_called()


class _FakeGraph:
    def __init__(self):
        self.config = None

    async def ainvoke(self, state, config):
        self.config = config
        return {"itinerary": "a plan"}


def _run_agent_with_fake_graph():
    from src.agent import graph as agent_module

    fake = _FakeGraph()
    with patch.object(agent_module, "build_agent_graph", return_value=fake):
        agent_module.run_agent("plan a trip", session=None)
    return fake


def test_run_agent_gives_the_graph_the_active_tracker():
    with track_usage() as tracker:
        fake = _run_agent_with_fake_graph()
    assert fake.config["callbacks"] == [tracker]


def test_run_agent_adds_no_callbacks_when_nothing_is_tracking():
    assert _run_agent_with_fake_graph().config["callbacks"] == []


def _start_call(tracker, run_id, model="claude-haiku-4-5"):
    tracker.on_chat_model_start({}, [[HumanMessage("plan a trip")]], run_id=run_id, invocation_params={"model": model})


def _end_call(tracker, run_id, message):
    tracker.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]), run_id=run_id)


def test_each_claude_call_becomes_a_datadog_llm_span_with_tokens_and_cost(monkeypatch, fake_ddtrace):
    llmobs, _ = fake_ddtrace
    monkeypatch.setattr(datadog, "_enabled", True)
    tracker, run = UsageTracker(), uuid4()

    _start_call(tracker, run)
    llmobs.llm.assert_called_once_with(model_name="claude-haiku-4-5", model_provider="anthropic", name="claude_call")
    assert llmobs.annotate.call_args.kwargs["input_data"] == [{"role": "user", "content": "plan a trip"}]

    _end_call(tracker, run, _reply(1000, 200))
    metrics = llmobs.annotate.call_args.kwargs["metrics"]
    assert metrics["total_tokens"] == 1200
    assert metrics["total_cost"] == pytest.approx(0.002)
    llmobs.llm.return_value.finish.assert_called_once()


def test_a_failed_call_closes_its_span_with_the_error(monkeypatch, fake_ddtrace):
    llmobs, _ = fake_ddtrace
    monkeypatch.setattr(datadog, "_enabled", True)
    tracker, run = UsageTracker(), uuid4()
    _start_call(tracker, run)

    tracker.on_llm_error(RuntimeError("rate limited"), run_id=run)

    span = llmobs.llm.return_value
    span.set_exc_info.assert_called_once()
    span.finish.assert_called_once()


def test_an_unknown_model_span_has_tokens_but_no_invented_cost(monkeypatch, fake_ddtrace):
    llmobs, _ = fake_ddtrace
    monkeypatch.setattr(datadog, "_enabled", True)
    tracker, run = UsageTracker(), uuid4()
    _start_call(tracker, run, model="some-future-model")
    _end_call(tracker, run, _reply(500, 100, model="some-future-model"))
    metrics = llmobs.annotate.call_args.kwargs["metrics"]
    assert metrics["total_tokens"] == 600
    assert "total_cost" not in metrics


def test_no_spans_are_created_when_datadog_is_off(fake_ddtrace):
    llmobs, _ = fake_ddtrace
    tracker, run = UsageTracker(), uuid4()
    _start_call(tracker, run)
    _end_call(tracker, run, _reply(100, 20))
    llmobs.llm.assert_not_called()
    assert tracker.total_tokens == 120


def test_a_datadog_problem_never_breaks_a_claude_call(monkeypatch, fake_ddtrace):
    llmobs, _ = fake_ddtrace
    monkeypatch.setattr(datadog, "_enabled", True)
    llmobs.llm.side_effect = RuntimeError("datadog unreachable")
    tracker, run = UsageTracker(), uuid4()
    _start_call(tracker, run)
    _end_call(tracker, run, _reply(100, 20))
    assert tracker.total_tokens == 120
