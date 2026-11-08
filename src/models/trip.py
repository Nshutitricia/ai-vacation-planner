from datetime import datetime
from typing import Optional

from pydantic import field_validator
from sqlmodel import SQLModel, Field

from src.guardrails.input_guard import validate_place_name, validate_trip_style


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

    # These strings are interpolated into the agent's prompt, so they are
    # checked here, which covers the REST routes and the voice flow alike.
    @field_validator("destination")
    @classmethod
    def destination_is_safe(cls, value: str) -> str:
        return validate_place_name(value)

    @field_validator("trip_style")
    @classmethod
    def trip_style_is_safe(cls, value: str) -> str:
        return validate_trip_style(value)


class TripResponse(SQLModel):
    id: int
    destination: str
    days: int
    budget: float
    trip_style: str
    user_id: int
    created_at: datetime