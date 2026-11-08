import os

# Must run before anything imports src.config: environment variables beat .env,
# so tests never send data to a real Datadog account even if .env enables it.
os.environ["DATADOG_ENABLED"] = "false"

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from src.config import settings
from src.models.itinerary import Itinerary
from src.models.trip import Trip
from src.models.user import User


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(element, compiler, **kw):
    # Tests run on in-memory SQLite; Postgres JSONB is rendered as plain JSON.
    return "JSON"


@pytest.fixture(autouse=True)
def classifier_off_by_default(monkeypatch):
    """Tests must never call the real Claude classifier unless they opt in."""
    monkeypatch.setattr(settings, "INJECTION_CLASSIFIER_ENABLED", False)


@pytest.fixture
def engine():
    """A fresh in-memory database with the tables the app code uses."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(
        engine, tables=[User.__table__, Trip.__table__, Itinerary.__table__]
    )
    yield engine
    engine.dispose()
