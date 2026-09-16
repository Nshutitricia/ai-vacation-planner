import json
from pydantic import ValidationError
from src.schemas.itinerary_schema import ItinerarySchema


class ResponseParser:

    def parse(self, response_text: str) -> ItinerarySchema:
        data = self._parse_json(response_text)
        return self._validate_schema(data)

    def _parse_json(self, response_text: str) -> dict:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {str(e)}")

    def _validate_schema(self, data: dict) -> ItinerarySchema:
        try:
            return ItinerarySchema(**data)
        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {str(e)}")