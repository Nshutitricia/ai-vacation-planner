import logging
from anthropic import Anthropic
from src.config import settings
from src.schemas.itinerary_schema import ItinerarySchema
from src.utils.llm.base import BaseLLM
from src.utils.llm.prompt_builder import PromptBuilder
from src.utils.llm.response_parser import ResponseParser
from src.utils.llm.tools import WeatherTool

logger = logging.getLogger(__name__)


class AnthropicLLM(BaseLLM):
    """
    Claude implementation of BaseLLM.
    Uses a tool calling loop — Claude decides when
    to call tools during generation.
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-haiku-4-5"
        self.prompt_builder = PromptBuilder()
        self.parser = ResponseParser()
        self.weather_tool = WeatherTool()
        self.max_tokens = 2048
        self.temperature = 0.3
        self.stop_sequences = []

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
        """
        Generate a structured itinerary using Claude.
        Claude decides when to call the weather tool.
        Returns a validated ItinerarySchema object.
        """
        logger.info(
            f"Generating itinerary for {destination} "
            f"using {self.model}"
        )

        messages = self.prompt_builder.build_messages(
            destination=destination,
            days=days,
            budget=budget,
            trip_style=trip_style
        )

        system = self.prompt_builder.get_system_prompt()

        response_text = self._run_tool_loop(messages, system)

        return self.parser.parse(response_text)

    def _run_tool(self, tool_name: str, tool_input: dict) -> str:
        """
        Run a tool by name and return the result as a string.
        Add more tools here as the app grows.
        """
        if tool_name == "get_weather":
            return self.weather_tool.process_tool_call(tool_input)

        return f"Unknown tool: {tool_name}"

    def _run_tool_loop(self, messages: list, system: str) -> str:
        iteration = 0
        while True:
            iteration += 1
            logger.info(f"--- Loop iteration {iteration} ---")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                tools=[self.weather_tool.definition],
                messages=messages,
                stop_sequences=self.stop_sequences
            )

            logger.info(f"Stop reason: {response.stop_reason}")
            logger.info(f"Content blocks: {[b.type for b in response.content]}")

            if response.stop_reason != "tool_use":
                logger.info("Claude finished — extracting text")
                text_blocks = [
                    b.text for b in response.content
                    if b.type == "text"
                ]
                return "\n".join(text_blocks)


            logger.info("Claude wants to call a tool")
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Tool called: {block.name}")
                    logger.info(f"Tool input: {block.input}")
                    result = self._run_tool(block.name, block.input)
                    logger.info(f"Tool result: {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({
                "role": "user",
                "content": tool_results
            })