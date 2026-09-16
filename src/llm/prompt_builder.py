from src.llm.system_prompts import ITINERARY_SYSTEM_PROMPT


class PromptBuilder:
    MAX_KNOWLEDGE_CHARS = 4000

    def build_messages(
        self,
        destination: str,
        days: int,
        budget: float,
        trip_style: str,
        weather: str = None,
        knowledge_context: list = None
    ) -> list:

        weather_section = ""
        if weather:
            weather_section = (
                f"\nCurrent weather in {destination}: {weather}"
                f"\nPlease consider the weather when suggesting activities."
            )

        knowledge_section = ""
        if knowledge_context:
            included = self._cap_knowledge_context(knowledge_context)
        else:
            included = []

        if included:
            notes = "\n".join(f"- {chunk}" for chunk in included)
            knowledge_section = (
                f"\nRetrieved travel knowledge:\n{notes}\n"
                f"\nIMPORTANT: Only use the above if it is genuinely about "
                f"{destination} itself. If any of it refers to a different "
                f"city, region, or country than {destination}, ignore that "
                f"part completely — do not mention it, and do not restructure "
                f"the itinerary (e.g. adding a day trip) just to make "
                f"unrelated content fit.\n"
            )

        prompt = f"""
Plan a {days}-day trip to {destination}.

Trip details:
- Total budget: ${budget}
- Travel style: {trip_style}
- Number of days: {days}
{weather_section}
{knowledge_section}

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

    def _cap_knowledge_context(self, chunks: list) -> list:
        included = []
        total_chars = 0
        for chunk in chunks:
            if total_chars + len(chunk) > self.MAX_KNOWLEDGE_CHARS:
                break
            included.append(chunk)
            total_chars += len(chunk)
        return included

    def get_system_prompt(self) -> str:
        return ITINERARY_SYSTEM_PROMPT

    def add_user_message(self, messages: list, content: str) -> None:
        messages.append({"role": "user", "content": content})

    def add_assistant_message(self, messages: list, content: str) -> None:
        messages.append({"role": "assistant", "content": content})