from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Trip(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    destination: str
    days: int
    budget: float
    trip_style: str
    user_id: int = Field(foreign_key='user.id')
    created_at: datetime = Field(default_factory= datetime.utcnow)

class TripCreate(SQLModel):
    destination: str
    days: int
    budget: float
    trip_style: str


class TripResponse(SQLModel):
    id: int
    destination: str
    days: int
    budget: float
    trip_style: str
    user_id: int
    created_at: datetime