import functools
import logging
import os

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
        # Datadog's other writers read the environment, and .env is only loaded
        # into our settings, so pass the values on explicitly.
        os.environ.setdefault("DD_API_KEY", settings.DD_API_KEY)
        os.environ.setdefault("DD_SITE", settings.DD_SITE)
        # The default 2s write timeout is too short for a TLS handshake plus
        # request on slower connections, and traces get dropped.
        os.environ.setdefault("DD_TRACE_AGENT_TIMEOUT_SECONDS", "10")

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

            # No automatic input/output capture: the arguments include user
            # records and database sessions, which must not leave the app.
            return workflow(name=name, _automatic_io_annotation=False)(func)(*args, **kwargs)

        return wrapper

    return decorator


def annotate(metadata: dict, metrics: dict) -> None:
    """Attach metadata and numeric metrics to the active span. A no-op unless enabled."""
    if not _enabled:
        return
    try:
        from ddtrace.llmobs import LLMObs

        LLMObs.annotate(metadata=metadata, metrics=metrics)
    except Exception:
        logger.warning("Could not attach usage to the Datadog span", exc_info=True)
