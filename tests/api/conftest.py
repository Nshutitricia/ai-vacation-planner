import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.database import get_session
from src.main import app
from src.schemas.itinerary_schema import ItinerarySchema


@pytest.fixture
def client(engine):
    """A client wired to the in-memory database. Auth is real: real hashing, real JWTs."""

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_and_login(client, username="alice") -> dict:
    """Create an account and return the Authorization header for it."""
    body = {"username": username, "email": f"{username}@example.com", "password": "secret123"}
    assert client.post("/auth/register", json=body).status_code == 201
    login = client.post("/auth/login", data={"username": username, "password": "secret123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def alice(client):
    return register_and_login(client, "alice")


@pytest.fixture
def bob(client):
    return register_and_login(client, "bob")


TRIP = {"destination": "Lisbon", "days": 3, "budget": 1200, "trip_style": "cultural"}


@pytest.fixture
def trip_id(client, alice) -> int:
    response = client.post("/trips", json=TRIP, headers=alice)
    assert response.status_code == 201
    return response.json()["id"]


def make_itinerary(destination="Lisbon", days=3, cost="$900") -> ItinerarySchema:
    return ItinerarySchema.model_validate({
        "destination": destination,
        "total_days": days,
        "estimated_total_cost": cost,
        "days": [
            {"day": n, "theme": f"Theme {n}", "activities": [
                {"name": "Walk", "description": "A stroll", "estimated_cost": "$0"}]}
            for n in range(1, days + 1)
        ],
    })
