import logging

from langchain_anthropic import ChatAnthropic

from src.config import settings

logger = logging.getLogger(__name__)

NARRATION_PROMPT = """
Summarize this itinerary as a short, natural spoken narration — like a
friendly travel guide giving someone the highlights out loud. No
markdown, no bullet points, no headers. Keep it brief: 3-5 sentences
total, mentioning the overall theme of the trip and one or two
standout activities per day — do NOT recite every single activity or
cost, this needs to stay short enough to actually listen to.

Itinerary data:
{itinerary_text}
"""


def narrate_itinerary(raw_summary: str) -> str:
    logger.info("Requesting Claude-generated flowing narration (Option B)")
    model = ChatAnthropic(model=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = model.invoke(NARRATION_PROMPT.format(itinerary_text=raw_summary))
        logger.info("Claude-generated narration succeeded (Option B)")
        return response.content
    except Exception as e:
        logger.warning(f"Claude-generated narration failed (Option B): {str(e)}")
        raise ValueError(f"Could not generate itinerary narration: {str(e)}") from e
