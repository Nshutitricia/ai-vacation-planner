from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Iterable

from pydantic import ValidationError

from src.guardrails.output_guard import find_problems, first_amount
from src.schemas.itinerary_schema import ItinerarySchema

VALID, COMPLETE, FORMAT, RELEVANT = "valid", "complete", "format", "relevant"

NO_COST_WORDS = ("free", "included", "no cost", "complimentary", "n/a", "none")


@dataclass
class CheckResult:
    name: str
    category: str
    passed: bool
    detail: str = ""


@dataclass
class EvaluationReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]


def evaluate_itinerary(
    itinerary: ItinerarySchema | dict,
    *,
    destination: str,
    days: int,
    budget: float,
    must_not_mention: Iterable[str] = (),
) -> EvaluationReport:
    """Score a generated itinerary with simple, deterministic checks.

    Free and repeatable, so it runs on every case. Questions about quality that
    need judgement (is the plan sensible?) are left to the LLM judge.
    """
    report = EvaluationReport()

    if isinstance(itinerary, dict):
        try:
            itinerary = ItinerarySchema.model_validate(itinerary)
        except ValidationError as e:
            report.results.append(CheckResult(
                "matches_schema", VALID, False, str(e.errors()[0]["msg"])
            ))
            return report
    report.results.append(CheckResult("matches_schema", VALID, True))

    trip = SimpleNamespace(destination=destination, days=days, budget=budget)
    problems = find_problems(itinerary, trip)
    report.results.append(CheckResult(
        "matches_trip", RELEVANT, not problems, "; ".join(problems)
    ))

    report.results.append(_activities_complete(itinerary))
    report.results.append(_costs_parseable(itinerary))
    report.results.append(_respects_exclusions(itinerary, must_not_mention))
    return report


def _activities_complete(itinerary: ItinerarySchema) -> CheckResult:
    empty = [
        f"day {d.day}: {a.name}"
        for d in itinerary.days
        for a in d.activities
        if not a.description.strip()
    ]
    themeless = [f"day {d.day}" for d in itinerary.days if not d.theme.strip()]
    problems = [f"no description: {e}" for e in empty] + [f"no theme: {t}" for t in themeless]
    return CheckResult("activities_complete", COMPLETE, not problems, "; ".join(problems))


def _costs_parseable(itinerary: ItinerarySchema) -> CheckResult:
    bad = [
        f"day {d.day}: {a.name} ('{a.estimated_cost}')"
        for d in itinerary.days
        for a in d.activities
        if first_amount(a.estimated_cost) is None
        and not any(word in a.estimated_cost.lower() for word in NO_COST_WORDS)
    ]
    if first_amount(itinerary.estimated_total_cost) is None:
        bad.append(f"total ('{itinerary.estimated_total_cost}')")
    return CheckResult("costs_parseable", FORMAT, not bad, "; ".join(bad))



def _respects_exclusions(itinerary: ItinerarySchema, forbidden: Iterable[str]) -> CheckResult:
    forbidden = [w.lower() for w in forbidden]
    hits = []
    for d in itinerary.days:
        text = " ".join([d.theme] + [f"{a.name} {a.description}" for a in d.activities]).lower()
        hits += [f"day {d.day}: '{w}'" for w in forbidden if w in text]
    return CheckResult("respects_exclusions", RELEVANT, not hits, "; ".join(hits))
