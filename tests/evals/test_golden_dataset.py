"""Offline checks on the golden dataset. No LLM calls, so these run on every test run."""
import pytest
from pydantic import ValidationError

from src.guardrails.errors import InputRejectedError
from src.guardrails.input_guard import validate_free_text
from src.models.trip import TripCreate
from tests.evals.dataset import GoldenCase, load_golden_dataset

CASES = load_golden_dataset()


def _by_category(*categories):
    return [c for c in CASES if c.category in categories]


def rejected_by_free_guards(case: GoldenCase) -> bool:
    """True if validation or the keyword guards (no LLM) stop this case."""
    try:
        TripCreate(**case.trip)
        if case.preferences:
            validate_free_text(case.preferences, "preferences", max_length=300)
    except (ValidationError, InputRejectedError):
        return True
    return False


def test_dataset_is_well_formed():
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids)), "case ids must be unique"
    assert len(CASES) >= 12
    assert {c.category for c in CASES} == {
        "standard", "edge", "preferences", "attack_blocked", "attack_needs_llm"
    }


@pytest.mark.parametrize("case", _by_category("standard", "edge", "preferences"), ids=lambda c: c.id)
def test_legitimate_cases_are_not_blocked(case):
    """Guardrails must not reject honest requests (false positives)."""
    assert case.expected.outcome == "itinerary"
    assert not rejected_by_free_guards(case)


@pytest.mark.parametrize("case", _by_category("attack_blocked"), ids=lambda c: c.id)
def test_attacks_are_rejected_without_calling_an_llm(case):
    assert case.expected.outcome == "rejected"
    assert rejected_by_free_guards(case)


@pytest.mark.parametrize("case", _by_category("attack_needs_llm"), ids=lambda c: c.id)
def test_paraphrased_attacks_are_a_known_gap_for_keyword_rules(case):
    """These slip past the keyword rules on purpose: only the LLM classifier can
    catch them. If the rules ever start catching one, move it to attack_blocked."""
    assert case.expected.needs_llm
    assert not rejected_by_free_guards(case)
