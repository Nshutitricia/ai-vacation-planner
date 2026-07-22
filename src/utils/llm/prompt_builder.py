class PromptBuilder:
    """
    Responsible for building prompts for LLM itinerary generation.
    """

    SYSTEM_PROMPT = """
You are an expert travel planner with deep knowledge of destinations worldwide.
Your job is to create realistic, detailed daily itineraries for travelers.

You must follow these rules:
1. Only suggest real places that actually exist at the destination
2. Activities must be realistic for the budget provided
3. Consider travel time between locations
4. Each day must have 3-5 activities
5. Activities must be specific real place names
6. Always include estimated costs for each activity
7. Always include a theme for each day

You must return a valid JSON object following this EXACT structure:
{
    "destination": "city name",
    "total_days": number,
    "estimated_total_cost": "cost range as string",
    "days": [
        {
            "day": 1,
            "theme": "theme for this day",
            "activities": [
                {
                    "name": "Place Name",
                    "description": "brief description",
                    "estimated_cost": "cost as string"
                }
            ]
        }
    ]
}
"""

    def build_user_prompt(
        self,
        destination: str,
        days: int,
        budget: float,
        trip_style: str,
        weather: str = None
    ) -> str:
        """
        Build the user prompt with trip details.
        Optionally includes weather information.
        """

        weather_section = ""
        if weather:
            weather_section = f"\nCurrent weather in {destination}: {weather}"
            weather_section += "\nPlease consider the weather when suggesting activities."

        return f"""
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

Important:
- Only suggest places actually in or near {destination}
- Stay within the ${budget} total budget
- Return exactly {days} day objects in the days array
- Every activity must have name, description and estimated_cost
- Every day must have a theme
"""

    def get_system_prompt(self) -> str:
        """Return the system prompt."""
        return self.SYSTEM_PROMPT

    def add_user_message(self, messages: list, content: str) -> None:
        """Add a user message to the messages list."""
        messages.append({"role": "user", "content": content})

    def add_assistant_message(self, messages: list, content: str) -> None:
        """Add an assistant message to the messages list."""
        messages.append({"role": "assistant", "content": content})

    def build_messages(
        self,
        destination: str,
        days: int,
        budget: float,
        trip_style: str,
        weather: str = None
    ) -> list:
        """
        Build the complete messages list for the LLM.
        Includes user prompt and assistant prefill.
        """
        messages = []

        user_prompt = self.build_user_prompt(
            destination=destination,
            days=days,
            budget=budget,
            trip_style=trip_style,
            weather=weather
        )

        self.add_user_message(messages, user_prompt)
        self.add_assistant_message(messages, "```json\n{")

        return messages