from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class Itinerary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key='trip.id', unique=True)
    days: List[dict] = Field(default=[], sa_column=Column(JSONB))

class ItineraryDay(SQLModel):
    day: int = Field(ge=1)
    activities: List[str] = Field(min_length=1)

class ItineraryCreate(SQLModel):
    trip_id: int  = Field(gt=0)
    days: List[ItineraryDay] = Field(min_length=1)

class ItineraryGenerate(SQLModel):
    trip_id: int = Field(gt=0)

class ItineraryResponse(SQLModel):
    trip_id: int
    days: List[ItineraryDay]
    message: str
