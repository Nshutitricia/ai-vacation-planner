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
    destination: str = Field(min_length=2, max_length=100)
    days: int = Field(ge=1, le=30)
    budget: float = Field(gt=0)
    trip_style: str = Field(min_length=2, max_length=50)


class TripResponse(SQLModel):
    id: int
    destination: str
    days: int
    budget: float
    trip_style: str
    user_id: int
    created_at: datetime