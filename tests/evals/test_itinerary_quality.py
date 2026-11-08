"""Live quality evaluation of real agent output.  Run in two steps:

    python scripts/generate_eval_outputs.py     # runs the agent, saves outputs
    pytest -m eval -v                           # judges the saved outputs

Generating once and judging many times keeps the cost of iterating low.
"""
import json
import os
from pathlib import Path

import pytest
from deepeval.metrics import GEval
from deepeval.models import AnthropicModel
from deepeval.test_case import LLMTestCase, SingleTurnParams

from src.evaluation.checks import evaluate_itinerary
from src.config import settings
from src.evaluation.render import itinerary_to_text, request_to_text
from src.schemas.itinerary_schema import ItinerarySchema
from tests.evals import report
from tests.evals.dataset import load_golden_dataset

pytestmark = pytest.mark.eval

OUTPUTS_PATH = Path(os.environ.get("EVAL_OUTPUTS") or Path(__file__).parent / "results" / "outputs.json")
THRESHOLD = 0.7
CASES = [c for c in load_golden_dataset() if c.expected.outcome == "itinerary"]


@pytest.fixture(scope="module")
def saved_outputs() -> dict:
    if not OUTPUTS_PATH.exists():
        pytest.skip("No saved outputs. Run: python scripts/generate_eval_outputs.py")
    return {r["id"]: r for r in json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))}


@pytest.fixture(scope="module")
def judge():
    return AnthropicModel(
        model=settings.EVAL_JUDGE_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
    )


def _result_for(case, saved_outputs) -> ItinerarySchema:
    result = saved_outputs.get(case.id)
    if result is None:
        pytest.skip(f"'{case.id}' was not generated")
    assert result["ok"], f"the agent failed to produce an itinerary: {result['error']}"
    return ItinerarySchema.model_validate(result["itinerary"])


def _request_text(case) -> str:
    return request_to_text(preferences=case.preferences, **case.trip)


def build_metrics(judge) -> list[GEval]:
    inputs = [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]
    return [
        GEval(
            name="Relevance to the request",
            evaluation_params=inputs,
            evaluation_steps=[
                "Check the itinerary is for the destination in the request.",
                "Check it covers the number of days asked for.",
                "Check the activities fit the requested travel style.",
                "Check the plan is plausible for the stated total budget. Spending less than the budget is fine and must not be penalised. If the budget is unrealistic for the destination, a plan that says so plainly is correct; one that pretends otherwise is not.",
                "If the request mentions preferences, check the itinerary respects every one, reading each by its ordinary meaning. For example, 'no museums' excludes museums and galleries, not outdoor ruins, churches or landmarks.",
            ],
            model=judge, threshold=THRESHOLD,
        ),
        GEval(
            name="Completeness and coherence",
            evaluation_params=inputs,
            evaluation_steps=[
                "Check every day has a clear theme and several concrete activities.",
                "Check activities have specific descriptions, not vague filler.",
                "Check the days are distinct and activities are not repeated.",
                "Check the order and amount of activities in a day is realistic.",
            ],
            model=judge, threshold=THRESHOLD,
        ),
        GEval(
            name="Meets the case criteria",
            evaluation_params=inputs + [SingleTurnParams.EXPECTED_OUTPUT],
            evaluation_steps=[
                "The expected output describes what a good answer must achieve.",
                "Check the actual output achieves it, and penalise any clear miss.",
                "Judge only what the expected output asks for; do not penalise the actual output for things the expected output does not mention.",
            ],
            model=judge, threshold=THRESHOLD,
        ),
    ]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_deterministic_quality(case, saved_outputs):
    itinerary = _result_for(case, saved_outputs)
    report = evaluate_itinerary(
        itinerary,
        destination=case.trip["destination"],
        days=case.trip["days"],
        budget=case.trip["budget"],
        must_not_mention=case.expected.must_not_mention,
    )
    assert report.passed, "; ".join(f"{r.name}: {r.detail}" for r in report.failures())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_llm_judged_quality(case, saved_outputs, judge):
    itinerary = _result_for(case, saved_outputs)
    request, plan = _request_text(case), itinerary_to_text(itinerary)
    test_case = LLMTestCase(input=request, actual_output=plan, expected_output=case.criteria)

    scores = []
    for metric in build_metrics(judge):
        metric.measure(test_case, _show_indicator=False)
        scores.append({
            "metric": metric.name,
            "score": metric.score,
            "threshold": metric.threshold,
            "passed": bool(metric.success),
            "reason": metric.reason,
        })
    report.record(case.id, request, plan, scores)

    failed = [s for s in scores if not s["passed"]]
    assert not failed, "; ".join(
        f"{s['metric']} scored {s['score']:.2f} (pass mark {s['threshold']}): {s['reason']}"
        for s in failed
    )
