import json
from pydantic import ValidationError
from src.schemas.itinerary_schema import ItinerarySchema


class ResponseParser:
    """
    Responsible for parsing and validating LLM responses.
    """

    def parse(self, response_text: str) -> ItinerarySchema:
        """
        Parse and validate the LLM response text.
        Returns a validated ItinerarySchema object.
        Raises ValueError if parsing or validation fails.
        """
        cleaned = self._clean_response(response_text)
        data = self._parse_json(cleaned)
        return self._validate_schema(data)

    def _clean_response(self, response_text: str) -> str:
        """
        Clean the raw LLM response text.
        Removes any markdown or extra whitespace.
        """
        cleaned = response_text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        if not cleaned.startswith("{"):
            cleaned = "{" + cleaned
        if not cleaned.endswith("}"):
            cleaned = cleaned + "}"

        return cleaned

    def _parse_json(self, cleaned_text: str) -> dict:
        """
        Parse the cleaned text into a Python dictionary.
        Raises ValueError if JSON is invalid.
        """
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {str(e)}")

    def _validate_schema(self, data: dict) -> ItinerarySchema:
        """
        Validate the parsed dictionary against ItinerarySchema.
        Raises ValueError if validation fails.
        """
        try:
            return ItinerarySchema(**data)
        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {str(e)}")