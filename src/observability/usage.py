import contextvars
import logging
import threading
from contextlib import contextmanager
from typing import Optional

from langchain_core.callbacks import BaseCallbackHandler

from src.observability import datadog

logger = logging.getLogger(__name__)

# USD per million tokens as (input, output). Check anthropic.com/pricing before
# relying on these. A model that is not listed gets token counts but no cost.
PRICES_PER_MILLION = {
    "claude-haiku-4-5": (1.00, 5.00),
}


def price_for(model: Optional[str]) -> Optional[tuple[float, float]]:
    """Look up by prefix, because API responses carry dated names like claude-haiku-4-5-20251001."""
    for name, price in PRICES_PER_MILLION.items():
        if model and model.startswith(name):
            return price
    return None


class UsageTracker(BaseCallbackHandler):
    """Adds up the tokens of every Claude call made while it is attached."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0
        self.model: Optional[str] = None
        self._lock = threading.Lock()

    def record(self, input_tokens: int, output_tokens: int, model: Optional[str] = None) -> None:
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.calls += 1
            self.model = model or self.model

    def on_llm_end(self, response, **kwargs) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None)
                if not usage:
                    continue
                model = (getattr(message, "response_metadata", None) or {}).get("model_name")
                self.record(usage.get("input_tokens", 0), usage.get("output_tokens", 0), model)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def costs(self) -> Optional[dict[str, float]]:
        price = price_for(self.model)
        if price is None:
            return None
        input_cost = self.input_tokens * price[0] / 1_000_000
        output_cost = self.output_tokens * price[1] / 1_000_000
        return {"input_cost": input_cost, "output_cost": output_cost, "total_cost": input_cost + output_cost}

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
    metrics = {
        "input_tokens": summary["input_tokens"],
        "output_tokens": summary["output_tokens"],
        "total_tokens": summary["total_tokens"],
    }
    costs = tracker.costs()
    if costs:
        metrics.update(costs)
    datadog.annotate(metadata={"usage": summary}, metrics=metrics)
