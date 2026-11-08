import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


class Expected(BaseModel):
    outcome: Literal["itinerary", "rejected"]
    needs_llm: bool = False
    must_not_mention: list[str] = Field(default_factory=list)


class GoldenCase(BaseModel):
    id: str
    category: Literal["standard", "edge", "preferences", "attack_blocked", "attack_needs_llm"]
    description: str
    trip: dict
    preferences: Optional[str] = None
    expected: Expected
    criteria: str


def load_golden_dataset() -> list[GoldenCase]:
    return [GoldenCase(**item) for item in json.loads(DATASET_PATH.read_text(encoding="utf-8"))]
