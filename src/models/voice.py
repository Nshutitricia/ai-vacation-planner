from sqlmodel import SQLModel

from src.models.itinerary import ItineraryDay


class VoicePlanResponse(SQLModel):
    transcribed_text: str
    trip_id: int
    days: list[ItineraryDay]
    message: str
