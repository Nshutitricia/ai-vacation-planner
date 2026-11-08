import contextvars
import logging
import threading
from contextlib import contextmanager
from typing import Optional

from langchain_core.callbacks import BaseCallbackHandler

from src.observability import datadog

logger = logging.getLogger(__name__)

PRICES_PER_MILLION = {
    "claude-haiku-4-5": (1.00, 5.00),
}


def price_for(model: Optional[str]) -> Optional[tuple[float, float]]:
    """Look up by prefix, because API responses carry dated names like claude-haiku-4-5-20251001."""
    for name, price in PRICES_PER_MILLION.items():
        if model and model.startswith(name):
            return price
    return None


def _costs(input_tokens: int, output_tokens: int, model: Optional[str]) -> Optional[dict[str, float]]:
    price = price_for(model)
    if price is None:
        return None
    input_cost = input_tokens * price[0] / 1_000_000
    output_cost = output_tokens * price[1] / 1_000_000
    return {"input_cost": input_cost, "output_cost": output_cost, "total_cost": input_cost + output_cost}


def _call_metrics(input_tokens: int, output_tokens: int, model: Optional[str]) -> dict[str, float]:
    """Token counts for one call, plus its cost when the model's price is known."""
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        **(_costs(input_tokens, output_tokens, model) or {}),
    }


def _as_chat(messages) -> list[dict]:
    roles = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}
    flat = messages[0] if messages and isinstance(messages[0], list) else messages
    return [{"role": roles.get(m.type, m.type), "content": str(m.content)} for m in flat]


def _tool_call_names(message) -> str:
    calls = getattr(message, "tool_calls", None) or []
    return "tool calls: " + ", ".join(c["name"] for c in calls) if calls else ""


class UsageTracker(BaseCallbackHandler):
    """Adds up the tokens of every Claude call made while it is attached."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0
        self.model: Optional[str] = None
        self._lock = threading.Lock()
        self._spans: dict = {}

    def record(self, input_tokens: int, output_tokens: int, model: Optional[str] = None) -> None:
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.calls += 1
            self.model = model or self.model

    def on_chat_model_start(self, serialized, messages, *, run_id=None, invocation_params=None, **kwargs) -> None:
        params = invocation_params or {}
        span = datadog.start_llm_span(params.get("model") or params.get("model_name"), _as_chat(messages))
        if span is not None:
            with self._lock:
                self._spans[run_id] = span

    def on_llm_end(self, response, *, run_id=None, **kwargs) -> None:
        call_metrics: dict[str, float] = {}
        output_text = ""
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None)
                output_text = output_text or generation.text or _tool_call_names(message)
                if not usage:
                    continue
                model = (getattr(message, "response_metadata", None) or {}).get("model_name")
                input_tokens, output_tokens = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
                self.record(input_tokens, output_tokens, model)
                call_metrics = _call_metrics(input_tokens, output_tokens, model)
        datadog.finish_llm_span(self._pop_span(run_id), output_text, call_metrics)

    def on_llm_error(self, error, *, run_id=None, **kwargs) -> None:
        datadog.finish_llm_span(self._pop_span(run_id), error=error)

    def _pop_span(self, run_id):
        with self._lock:
            return self._spans.pop(run_id, None)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def costs(self) -> Optional[dict[str, float]]:
        return _costs(self.input_tokens, self.output_tokens, self.model)

    def as_dict(self) -> dict:
        costs = self.costs()
        return {
            "model": self.model,
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(costs["total_cost"], 6) if costs else None,
        }


_current: contextvars.ContextVar[Optional[UsageTracker]] = contextvars.ContextVar("usage_tracker", default=None)


@contextmanager
def track_usage():
    """Count the tokens of every agent call made inside the block, across retries."""
    tracker = UsageTracker()
    token = _current.set(tracker)
    try:
        yield tracker
    finally:
        _current.reset(token)


def current_tracker() -> Optional[UsageTracker]:
    return _current.get()


def report_usage(tracker: UsageTracker, label: str) -> None:
    """Log the usage and attach it to the active Datadog span."""
    if not tracker.calls:
        return
    summary = tracker.as_dict()
    cost = summary["estimated_cost_usd"]
    logger.info(
        f"LLM usage for {label}: model={summary['model']} calls={summary['calls']} "
        f"input_tokens={summary['input_tokens']} output_tokens={summary['output_tokens']} "
        f"estimated_cost={'$' + format(cost, '.4f') if cost is not None else 'n/a'}"
    )
    datadog.annotate(metadata={"usage": summary})
