"""Send one test trace to Datadog and report what happened.

    python scripts/send_datadog_test_trace.py

Starts Datadog exactly as the app does, records a small workflow span, forces
the upload, and prints any error. Look for the trace named
"datadog_connectivity_test" under LLM Observability > Traces.
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.observability import datadog

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("ddtrace.llmobs").setLevel(logging.DEBUG)


@datadog.traced("datadog_connectivity_test")
def tiny_job() -> str:
    time.sleep(0.2)
    return "done"


if __name__ == "__main__":
    print(f"DATADOG_ENABLED={settings.DATADOG_ENABLED}  site={settings.DD_SITE}  service={settings.DD_SERVICE}")
    started = datadog.init_datadog()
    print(f"init_datadog() returned: {started}")
    if not started:
        sys.exit("Datadog did not start. Check DATADOG_ENABLED=true and DD_API_KEY in .env")

    from ddtrace.llmobs import LLMObs

    print(f"LLMObs.enabled: {LLMObs.enabled}")
    print(f"tiny_job() -> {tiny_job()}")
    print("Flushing...")
    LLMObs.flush()
    time.sleep(3)
    print("Done. Look in Datadog > LLM Observability > Traces for 'datadog_connectivity_test'.")
