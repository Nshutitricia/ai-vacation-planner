"""Collects every judge score (passes included) and turns them into a report."""
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

# One entry per judged case. Filled in by the eval tests.
ENTRIES: list[dict] = []


def record(case_id: str, request: str, plan: str, scores: list[dict]) -> None:
    ENTRIES.append({"case": case_id, "request": request, "plan": plan, "scores": scores})


def format_table(entries: list[dict]) -> str:
    """A compact score table. A * marks a score below the pass mark."""
    metrics = [s["metric"] for s in entries[0]["scores"]]
    width = max(len(e["case"]) for e in entries)
    header = "case".ljust(width) + "  " + "  ".join(m[:24].ljust(24) for m in metrics)
    lines = [header, "-" * len(header)]
    for e in entries:
        cells = []
        for s in e["scores"]:
            mark = " " if s["passed"] else "*"
            cells.append(f"{s['score']:.2f}{mark}".ljust(24))
        lines.append(e["case"].ljust(width) + "  " + "  ".join(cells))

    averages = []
    for i, _ in enumerate(metrics):
        values = [e["scores"][i]["score"] for e in entries]
        averages.append(f"{sum(values) / len(values):.2f} ".ljust(24))
    lines.append("-" * len(header))
    lines.append("average".ljust(width) + "  " + "  ".join(averages))
    lines.append("")
    lines.append(f"* = below the pass mark ({entries[0]['scores'][0]['threshold']})")
    return "\n".join(lines)


def format_markdown(entries: list[dict]) -> str:
    out = ["# LLM judge report", "", format_table_md(entries), ""]
    for e in entries:
        out += [f"## {e['case']}", "", f"**Request:** {e['request']}", ""]
        for s in e["scores"]:
            status = "pass" if s["passed"] else "FAIL"
            out += [f"- **{s['metric']}**: {s['score']:.2f} (pass mark {s['threshold']}) - {status}",
                    f"  - {s['reason']}"]
        out += ["", "<details><summary>Plan that was judged</summary>", "", "```", e["plan"], "```", "", "</details>", ""]
    return "\n".join(out)


def format_table_md(entries: list[dict]) -> str:
    metrics = [s["metric"] for s in entries[0]["scores"]]
    rows = ["| case | " + " | ".join(metrics) + " |", "|---|" + "---|" * len(metrics)]
    for e in entries:
        cells = [f"{s['score']:.2f}" + ("" if s["passed"] else " (fail)") for s in e["scores"]]
        rows.append(f"| {e['case']} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def write_reports(entries: list[dict], directory: Path = RESULTS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "judge_report.json").write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown = directory / "judge_report.md"
    markdown.write_text(format_markdown(entries), encoding="utf-8")
    return markdown
