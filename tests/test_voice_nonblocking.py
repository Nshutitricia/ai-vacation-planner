import threading
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.models.itinerary import Itinerary
from src.models.user import User
from src.database import get_session
from src.utils.deps import get_current_user


def test_slow_voice_request_does_not_block_other_requests():
    started = threading.Event()

    def slow_plan(self, path, user, session):
        started.set()
        time.sleep(1.5)
        from src.models.trip import TripCreate
        from src.services.voice_service import VoicePlanResult
        return VoicePlanResult(
            transcribed_text="hi",
            trip=TripCreate(destination="Lisbon", days=2, budget=900, trip_style="cultural"),
            preferences=None,
            inferred_fields=[],
            itinerary=Itinerary(trip_id=1, days=[]),
        )

    app.dependency_overrides[get_current_user] = lambda: User(id=1, email="a@b.c", hashed_password="x")
    app.dependency_overrides[get_session] = lambda: None
    try:
        with patch("src.services.voice_service.VoiceService.plan_trip_from_audio", slow_plan):
            # `with` makes all requests share one event loop, like a real server.
            with TestClient(app) as client:
                t = threading.Thread(
                    target=lambda: client.post(
                        "/voice/plan", files={"audio": ("a.wav", b"x", "audio/wav")}
                    )
                )
                t.start()
                assert started.wait(2)
                t0 = time.time()
                client.get("/openapi.json")
                elapsed = time.time() - t0
                t.join()
        assert elapsed < 1.0, f"other request waited {elapsed:.2f}s behind voice processing"
    finally:
        app.dependency_overrides.clear()
