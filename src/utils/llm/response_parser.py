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

        The LLM call uses output_config with a JSON schema, so Claude's
        response text is already guaranteed to be a bare, schema-conformant
        JSON object with no markdown fences or extra prose to strip out.
        """
        data = self._parse_json(response_text)
        return self._validate_schema(data)

    def _parse_json(self, response_text: str) -> dict:
        """
        Parse the response text into a Python dictionary.
        Raises ValueError if JSON is invalid.
        """
        try:
            return json.loads(response_text)
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