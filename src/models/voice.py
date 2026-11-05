from typing import Optional

from sqlmodel import SQLModel

from src.models.itinerary import ItineraryDay
from src.models.trip import TripCreate


class VoicePlanResponse(SQLModel):
    transcribed_text: str
    trip_id: int
    trip_details: TripCreate
    preferences: Optional[str] = None
    inferred_fields: list[str] = []
    days: list[ItineraryDay]
    message: str
