from langchain_anthropic import ChatAnthropic

from src.config import settings
from src.models.trip import TripCreate

EXTRACTION_PROMPT = """
Extract the trip details from this spoken request and return them in
the required structure. The travel style must be one of: budget,
luxury, adventure, cultural, family — pick whichever fits best even if
not stated explicitly. If the budget isn't mentioned, make a
reasonable estimate based on the travel style and trip length.

Spoken request: "{text}"
"""


def extract_trip_details(transcribed_text: str) -> TripCreate:

    model = ChatAnthropic(model=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY)
    structured_model = model.with_structured_output(TripCreate)

    try:
        return structured_model.invoke(
            EXTRACTION_PROMPT.format(text=transcribed_text)
        )
    except Exception as e:
        raise ValueError(
            f"Could not extract trip details from speech: {str(e)}"
        ) from e
