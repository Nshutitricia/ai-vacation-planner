from unittest.mock import patch

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from src.agent.voice.extraction import ExtractedTrip
from src.models.itinerary import Itinerary
from src.models.trip import Trip, TripCreate
from src.models.user import User
from src.schemas.itinerary_schema import ItinerarySchema
from src.services.voice_service import VoiceService


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(element, compiler, **kw):
    # Tests run on in-memory SQLite; Postgres JSONB is rendered as plain JSON.
    return "JSON"


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(
        engine, tables=[User.__table__, Trip.__table__, Itinerary.__table__]
    )
    with Session(engine) as s:
        user = User(username="tester", email="a@b.c", hashed_password="x")
        s.add(user)
        s.commit()
        s.refresh(user)
        yield s


def _extracted(preferences="no museums", inferred=None):
    return ExtractedTrip(
        trip=TripCreate(destination="Lisbon", days=2, budget=900, trip_style="cultural"),
        preferences=preferences,
        inferred_fields=inferred or [],
    )


SCHEMA = ItinerarySchema.model_validate({
    "destination": "Lisbon",
    "total_days": 1,
    "estimated_total_cost": "$100",
    "days": [{"day": 1, "theme": "Old town", "activities": [
        {"name": "Walk", "description": "Stroll", "estimated_cost": "$0"}]}]
})


def _plan(session, run_agent):
    user = session.exec(select(User)).first()
    with patch("src.services.voice_service.transcribe_audio", return_value="text"), \
         patch("src.services.voice_service.extract_trip_details", return_value=_extracted(inferred=["budget"])), \
         patch("src.services.itinerary_service.run_agent", run_agent):
        return VoiceService().plan_trip_from_audio("x.wav", user, session)


def test_preferences_reach_the_agent_request(session):
    seen = {}

    def fake_agent(request, sess):
        seen["request"] = request
        return SCHEMA

    result = _plan(session, fake_agent)
    assert "no museums" in seen["request"]
    assert "Lisbon" in seen["request"]
    assert result.inferred_fields == ["budget"]


def test_success_saves_trip_and_itinerary(session):
    _plan(session, lambda r, s: SCHEMA)
    assert len(session.exec(select(Trip)).all()) == 1
    assert len(session.exec(select(Itinerary)).all()) == 1


def test_agent_failure_leaves_no_orphan_trip(session):
    def boom(request, sess):
        raise RuntimeError("claude down")

    with pytest.raises(RuntimeError):
        _plan(session, boom)
    assert session.exec(select(Trip)).all() == []
    assert session.exec(select(Itinerary)).all() == []
