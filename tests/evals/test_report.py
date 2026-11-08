"""Offline checks of the report formatting. No LLM calls."""
from tests.evals import report


def _entry(case, scores):
    return {
        "case": case, "request": "Plan a trip.", "plan": "Day 1: Walk",
        "scores": [
            {"metric": name, "score": score, "threshold": 0.7, "passed": score >= 0.7, "reason": f"because {name}"}
            for name, score in scores
        ],
    }


ENTRIES = [
    _entry("lisbon", [("Relevance", 0.9), ("Completeness", 0.8)]),
    _entry("paris", [("Relevance", 0.8), ("Completeness", 0.6)]),
]


def test_table_shows_every_score_marks_failures_and_averages():
    table = report.format_table(ENTRIES)
    assert "0.90" in table and "0.80" in table
    assert "0.60*" in table
    assert "average" in table and "0.85" in table


def test_markdown_report_keeps_reasons_and_the_judged_plan():
    markdown = report.format_markdown(ENTRIES)
    assert "because Completeness" in markdown
    assert "Day 1: Walk" in markdown
    assert "| paris | 0.80 | 0.60 (fail) |" in markdown


def test_reports_are_written_to_disk(tmp_path):
    path = report.write_reports(ENTRIES, tmp_path)
    assert path.read_text(encoding="utf-8").startswith("# LLM judge report")
    assert (tmp_path / "judge_report.json").exists()
