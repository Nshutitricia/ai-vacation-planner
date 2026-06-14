from datetime import datetime
from typing import Optional

from pydantic import field_validator
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True,index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    password: str = Field(min_length=6, max_length=72)

class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    created_at: datetime