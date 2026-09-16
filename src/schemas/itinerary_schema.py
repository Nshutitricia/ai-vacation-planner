from pydantic import BaseModel, field_validator
from typing import List

class ActivitySchema(BaseModel):
    name: str
    description: str
    estimated_cost: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if v.strip() == "":
            raise ValueError("Activity name cannot be empty")
        return v.strip()

    @field_validator("estimated_cost")
    @classmethod
    def cost_not_empty(cls, v: str) -> str:
        if v.strip() == "":
            raise ValueError("Estimated cost cannot be empty")
        return v.strip()

class DaySchema(BaseModel):
    day: int
    theme: str
    activities: List[ActivitySchema]

    @field_validator("day")
    @classmethod
    def day_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Day number must be at least 1")
        return v

    @field_validator("activities")
    @classmethod
    def must_have_activities(cls, v: List[ActivitySchema]) -> List[ActivitySchema]:
        if len(v) == 0:
            raise ValueError("Each day must have at least one activity")
        return v

class ItinerarySchema(BaseModel):
    destination: str
    total_days: int
    estimated_total_cost: str
    days: List[DaySchema]

    @field_validator("total_days")
    @classmethod
    def total_days_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Total days must be at least 1")
        return v

    @field_validator("days")
    @classmethod
    def days_must_match_total(cls, v: List[DaySchema], info) -> List[DaySchema]:
        if "total_days" in info.data:
            if len(v) != info.data["total_days"]:
                raise ValueError(
                    f"Number of days ({len(v)}) must match "
                    f"total_days ({info.data['total_days']})"
                )
        return v

    @classmethod
    def output_json_schema(cls) -> dict:
        schema = cls.model_json_schema()
        _forbid_additional_properties(schema)
        return schema


def _forbid_additional_properties(node) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object":
            node["additionalProperties"] = False
        for value in node.values():
            _forbid_additional_properties(value)
    elif isinstance(node, list):
        for item in node:
            _forbid_additional_properties(item)