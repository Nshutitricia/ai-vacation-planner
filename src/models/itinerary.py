from datetime import datetime
from typing import Optional, List, Union

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class Itinerary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key='trip.id', unique=True)
    days: List[dict] = Field(default=[], sa_column=Column(JSONB))

class ActivityDetail(SQLModel):

    name: str
    description: str
    estimated_cost: str


class ItineraryDay(SQLModel):
    day: int
    theme: Optional[str] = None
    activities: List[Union[ActivityDetail, str]]


class ItineraryCreate(SQLModel):
    trip_id: int
    days: List["ItineraryDayCreate"]


class ItineraryDayCreate(SQLModel):
    day: int
    activities: List[str]


class ItineraryGenerate(SQLModel):
    trip_id: int = Field(gt=0)


class ItineraryResponse(SQLModel):
    trip_id: int
    days: List[ItineraryDay]
    message: str