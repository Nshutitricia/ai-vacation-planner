import functools
import logging
import os
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

_enabled = False


def init_datadog() -> bool:
    """Start Datadog LLM Observability if it is switched on and configured.

    Sends data straight to Datadog (agentless), so no local Datadog Agent is
    needed. Monitoring must never take the app down, so any problem here is
    logged and the app carries on without it.
    """
    global _enabled
    if not settings.DATADOG_ENABLED:
        return False
    if not settings.DD_API_KEY:
        logger.warning("DATADOG_ENABLED is true but DD_API_KEY is empty; observability is off")
        return False
    try:
        os.environ.setdefault("DD_API_KEY", settings.DD_API_KEY)
        os.environ.setdefault("DD_SITE", settings.DD_SITE)
        os.environ.setdefault("DD_TRACE_AGENT_TIMEOUT_SECONDS", "10")
        os.environ.setdefault("DD_TRACE_LANGCHAIN_ENABLED", "false")
        os.environ.setdefault("DD_TRACE_ANTHROPIC_ENABLED", "false")

        from ddtrace.llmobs import LLMObs

        LLMObs.enable(
            ml_app=settings.DD_SERVICE,
            api_key=settings.DD_API_KEY,
            site=settings.DD_SITE,
            service=settings.DD_SERVICE,
            env=settings.DD_ENV,
            agentless_enabled=True,
        )
    except Exception:
        logger.exception("Could not start Datadog LLM Observability; continuing without it")
        return False
    _enabled = True
    logger.info(f"Datadog LLM Observability enabled (site={settings.DD_SITE}, service={settings.DD_SERVICE})")
    return True


def traced(name: str):
    """Record a function call as a Datadog span: duration, and any error it raises.

    A no-op unless Datadog is enabled, so it is safe to put on any function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not _enabled:
                return func(*args, **kwargs)
            from ddtrace.llmobs.decorators import workflow

            return workflow(name=name, _automatic_io_annotation=False)(func)(*args, **kwargs)

        return wrapper

    return decorator


def annotate(metadata: dict) -> None:
    """Attach readable metadata to the active span. A no-op unless enabled."""
    if not _enabled:
        return
    try:
        from ddtrace.llmobs import LLMObs

        LLMObs.annotate(metadata=metadata)
    except Exception:
        logger.warning("Could not attach usage to the Datadog span", exc_info=True)


def start_llm_span(model_name: Optional[str], input_messages: list[dict]):
    """Open a Datadog LLM span for one Claude call. Returns None when disabled."""
    if not _enabled:
        return None
    try:
        from ddtrace.llmobs import LLMObs

        span = LLMObs.llm(model_name=model_name or "unknown", model_provider="anthropic", name="claude_call")
        LLMObs.annotate(span=span, input_data=input_messages)
        return span
    except Exception:
        logger.warning("Could not start a Datadog LLM span", exc_info=True)
        return None


def finish_llm_span(span, output_text: str = "", metrics: Optional[dict] = None, error: Optional[BaseException] = None) -> None:
    """Close the span opened by start_llm_span, with its tokens and cost, or its error."""
    if span is None:
        return
    try:
        from ddtrace.llmobs import LLMObs

        if error is not None:
            span.set_exc_info(type(error), error, error.__traceback__)
        else:
            LLMObs.annotate(span=span, output_data=output_text, metrics=metrics or {})
    except Exception:
        logger.warning("Could not annotate a Datadog LLM span", exc_info=True)
    finally:
        span.finish()
