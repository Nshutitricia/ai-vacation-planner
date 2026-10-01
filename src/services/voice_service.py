from sqlmodel import Session

from src.agent.voice.extraction import extract_trip_details
from src.agent.voice.transcription import transcribe_audio
from src.models.itinerary import Itinerary
from src.models.user import User
from src.services.itinerary_service import ItineraryService
from src.services.trip_service import TripService


class VoiceService:

    def __init__(self):
        self.trip_service = TripService()
        self.itinerary_service = ItineraryService()

    def plan_trip_from_audio(
        self,
        audio_path: str,
        user: User,
        session: Session
    ) -> tuple[str, Itinerary]:

        transcribed_text = transcribe_audio(audio_path)
        trip_data = extract_trip_details(transcribed_text)
        trip = self.trip_service.create(trip_data, user_id=user.id, session=session)
        itinerary = self.itinerary_service.generate(trip=trip, session=session)
        return transcribed_text, itinerary
