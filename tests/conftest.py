import pytest

from src.config import settings


@pytest.fixture(autouse=True)
def classifier_off_by_default(monkeypatch):
    """Tests must never call the real Claude classifier unless they opt in."""
    monkeypatch.setattr(settings, "INJECTION_CLASSIFIER_ENABLED", False)
