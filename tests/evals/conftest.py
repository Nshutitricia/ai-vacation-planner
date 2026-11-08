import os

# Keep DeepEval from sending usage data or prompting to log in to Confident AI.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

from tests.evals import report  # noqa: E402


def pytest_terminal_summary(terminalreporter):
    """After a judged run, print every score and save the full report."""
    if not report.ENTRIES:
        return
    terminalreporter.section("LLM judge scores")
    terminalreporter.write_line(report.format_table(report.ENTRIES))
    path = report.write_reports(report.ENTRIES)
    terminalreporter.write_line("")
    terminalreporter.write_line(f"Full report with reasons and judged plans: {path}")
