"""Live checks of the LLM injection classifier against the golden dataset.

    pytest -m eval -v -k classifier
"""
import pytest

from src.config import settings
from src.guardrails.errors import InputRejectedError
from src.guardrails.injection_classifier import classify_free_text
from tests.evals.dataset import load_golden_dataset

pytestmark = pytest.mark.eval

CASES = load_golden_dataset()
ATTACKS = [c for c in CASES if c.category == "attack_needs_llm"]
HONEST_PREFERENCES = [c for c in CASES if c.expected.outcome == "itinerary" and c.preferences]


@pytest.fixture(autouse=True)
def classifier_on(monkeypatch):
    monkeypatch.setattr(settings, "INJECTION_CLASSIFIER_ENABLED", True)


@pytest.mark.parametrize("case", ATTACKS, ids=lambda c: c.id)
def test_classifier_catches_attacks_the_keyword_rules_miss(case):
    with pytest.raises(InputRejectedError):
        classify_free_text(case.preferences, "preferences")


@pytest.mark.parametrize("case", HONEST_PREFERENCES, ids=lambda c: c.id)
def test_classifier_does_not_reject_honest_preferences(case):
    classify_free_text(case.preferences, "preferences")
