import os

import pytest

from src.config import settings
from src.observability import datadog


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    for name in (
        "DD_API_KEY", "DD_SITE", "DD_TRACE_AGENT_TIMEOUT_SECONDS",
        "DD_TRACE_LANGCHAIN_ENABLED", "DD_TRACE_ANTHROPIC_ENABLED",
    ):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)
    monkeypatch.setattr(datadog, "_enabled", False)
    monkeypatch.setattr(settings, "DATADOG_ENABLED", False)
    monkeypatch.setattr(settings, "DD_API_KEY", "")


def _enable(monkeypatch):
    monkeypatch.setattr(settings, "DATADOG_ENABLED", True)
    monkeypatch.setattr(settings, "DD_API_KEY", "test-key")


def test_nothing_starts_when_switched_off(fake_ddtrace):
    llmobs, _ = fake_ddtrace
    assert datadog.init_datadog() is False
    llmobs.enable.assert_not_called()


def test_enabled_without_a_key_stays_off_and_does_not_crash(monkeypatch, fake_ddtrace):
    monkeypatch.setattr(settings, "DATADOG_ENABLED", True)
    llmobs, _ = fake_ddtrace
    assert datadog.init_datadog() is False
    llmobs.enable.assert_not_called()


def test_enabled_starts_agentless_with_the_configured_site_and_key(monkeypatch, fake_ddtrace):
    _enable(monkeypatch)
    llmobs, _ = fake_ddtrace
    assert datadog.init_datadog() is True
    kwargs = llmobs.enable.call_args.kwargs
    assert kwargs["agentless_enabled"] is True
    assert kwargs["api_key"] == "test-key"
    assert kwargs["site"] == settings.DD_SITE
    assert kwargs["ml_app"] == settings.DD_SERVICE


def test_the_key_and_site_are_exported_for_datadogs_other_writers(monkeypatch, fake_ddtrace):
    _enable(monkeypatch)
    datadog.init_datadog()
    assert os.environ["DD_API_KEY"] == "test-key"
    assert os.environ["DD_SITE"] == settings.DD_SITE
    assert float(os.environ["DD_TRACE_AGENT_TIMEOUT_SECONDS"]) >= 5


def test_automatic_llm_spans_are_off_so_calls_are_not_counted_twice(monkeypatch, fake_ddtrace):
    for name in ("DD_TRACE_LANGCHAIN_ENABLED", "DD_TRACE_ANTHROPIC_ENABLED"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)
    _enable(monkeypatch)
    datadog.init_datadog()
    assert os.environ["DD_TRACE_LANGCHAIN_ENABLED"] == "false"
    assert os.environ["DD_TRACE_ANTHROPIC_ENABLED"] == "false"


def test_a_datadog_failure_never_stops_the_app(monkeypatch, fake_ddtrace):
    _enable(monkeypatch)
    llmobs, _ = fake_ddtrace
    llmobs.enable.side_effect = RuntimeError("datadog unreachable")
    assert datadog.init_datadog() is False


def test_traced_does_nothing_when_off(fake_ddtrace):
    _, workflow = fake_ddtrace

    @datadog.traced("generate")
    def add(a, b):
        return a + b

    assert add(1, 2) == 3
    workflow.assert_not_called()


def test_traced_passes_errors_through_untouched(fake_ddtrace):
    @datadog.traced("generate")
    def boom():
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        boom()


def test_traced_records_a_span_when_on(monkeypatch, fake_ddtrace):
    monkeypatch.setattr(datadog, "_enabled", True)
    _, workflow = fake_ddtrace

    @datadog.traced("generate_itinerary")
    def add(a, b):
        return a + b

    assert add(2, 3) == 5
    workflow.assert_called_once_with(name="generate_itinerary", _automatic_io_annotation=False)


def test_spans_never_capture_function_arguments(monkeypatch, fake_ddtrace):
    """Arguments can hold user records (with password hashes) and DB sessions."""
    monkeypatch.setattr(datadog, "_enabled", True)
    _, workflow = fake_ddtrace

    @datadog.traced("anything")
    def handler(user):
        return "ok"

    handler({"hashed_password": "secret"})
    assert workflow.call_args.kwargs["_automatic_io_annotation"] is False


def test_the_test_suite_never_sends_data_to_datadog():
    """conftest forces Datadog off even when .env enables it, so tests cannot report to a real account."""
    assert os.environ["DATADOG_ENABLED"] == "false"
    assert datadog._enabled is False
