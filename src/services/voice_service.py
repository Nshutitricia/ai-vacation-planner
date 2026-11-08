from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session

from src.agent.voice.extraction import extract_trip_details
from src.agent.voice.transcription import transcribe_audio
from src.models.itinerary import Itinerary
from src.models.trip import TripCreate
from src.models.user import User
from src.observability.datadog import traced
from src.services.itinerary_service import ItineraryService
from src.services.trip_service import TripService


@dataclass
class VoicePlanResult:
    transcribed_text: str
    trip: TripCreate
    preferences: Optional[str]
    inferred_fields: list[str]
    itinerary: Itinerary


class VoiceService:

    def __init__(self):
        self.trip_service = TripService()
        self.itinerary_service = ItineraryService()

    @traced("plan_trip_from_voice")
    def plan_trip_from_audio(
        self,
        audio_path: str,
        user: User,
        session: Session
    ) -> VoicePlanResult:

        transcribed_text = transcribe_audio(audio_path)
        extracted = extract_trip_details(transcribed_text)

        # Trip and itinerary are saved in ONE transaction: if generation
        # fails, nothing is left behind (no orphan trip).
        try:
            trip = self.trip_service.create(
                extracted.trip, user_id=user.id, session=session, commit=False
            )
            itinerary = self.itinerary_service.generate(
                trip=trip,
                session=session,
                preferences=extracted.preferences,
                commit=False
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        session.refresh(itinerary)

        return VoicePlanResult(
            transcribed_text=transcribed_text,
            trip=extracted.trip,
            preferences=extracted.preferences,
            inferred_fields=extracted.inferred_fields,
            itinerary=itinerary,
        )
