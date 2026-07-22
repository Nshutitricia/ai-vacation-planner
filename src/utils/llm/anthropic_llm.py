import logging
from anthropic import Anthropic
from src.config import settings
from src.schemas.itinerary_schema import ItinerarySchema
from src.utils.llm.base import BaseLLM
from src.utils.llm.prompt_builder import PromptBuilder
from src.utils.llm.response_parser import ResponseParser

logger = logging.getLogger(__name__)

class AnthropicLLM(BaseLLM):
    """
    Claude implementation of BaseLLM.
    Uses Anthropic's API to generate itineraries.
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-haiku-4-5"
        self.prompt_builder = PromptBuilder()
        self.parser = ResponseParser()
        self.max_tokens = 2048
        self.temperature = 0.3
        self.stop_sequences = ["```"]

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "anthropic"

    def generate_itinerary(
        self,
        destination: str,
        days: int,
        budget: float,
        trip_style: str,
        weather: str = None
    ) -> ItinerarySchema:

        logger.info(
            f"Generating itinerary for {destination} "
            f"using {self.model}"
        )

        messages = self.prompt_builder.build_messages(
            destination=destination,
            days=days,
            budget=budget,
            trip_style=trip_style,
            weather=weather
        )

        system = self.prompt_builder.get_system_prompt()

        response = self._call_api(messages, system)

        return self.parser.parse(response)

    def _call_api(self, messages: list, system: str) -> str:

        try:
            logger.info(f"Calling Anthropic API with model {self.model}")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=messages,
                stop_sequences=self.stop_sequences
            )

            response_text = "{" + message.content[0].text

            logger.info("Anthropic API call successful")

            return response_text

        except Exception as e:
            raise ValueError(f"Anthropic API call failed: {str(e)}")