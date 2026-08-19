from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import SQLModel, Field

from src.config import settings


class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "knowledge_chunk"

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    source: str = Field(index=True)
    category: str = Field(index=True)
    embedding: list[float] = Field(
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
