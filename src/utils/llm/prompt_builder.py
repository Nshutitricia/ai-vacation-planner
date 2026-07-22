from src.utils.llm.system_prompts import ITINERARY_SYSTEM_PROMPT


class PromptBuilder:

    def build_messages(
        self,
        destination: str,
        days: int,
        budget: float,
        trip_style: str,
        weather: str = None
    ) -> list:

        weather_section = ""
        if weather:
            weather_section = (
                f"\nCurrent weather in {destination}: {weather}"
                f"\nPlease consider the weather when suggesting activities."
            )

        prompt = f"""
Plan a {days}-day trip to {destination}.

Trip details:
- Total budget: ${budget}
- Travel style: {trip_style}
- Number of days: {days}
{weather_section}

Travel style guide:
- budget: Free or low-cost attractions, street food, public transport
- luxury: High-end restaurants, private tours, premium experiences
- adventure: Outdoor activities, hiking, extreme sports
- cultural: Museums, historical sites, local traditions
- family: Family-friendly activities suitable for all ages

IMPORTANT: First call get_weather tool for {destination},
then create the itinerary based on the weather.
"""

        messages = []
        self.add_user_message(messages, prompt)
        return messages

    def get_system_prompt(self) -> str:
        return ITINERARY_SYSTEM_PROMPT

    def add_user_message(self, messages: list, content: str) -> None:
        messages.append({"role": "user", "content": content})

    def add_assistant_message(self, messages: list, content: str) -> None:
        messages.append({"role": "assistant", "content": content})