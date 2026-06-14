import json
from anthropic import Anthropic
from src.config import settings

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
model = "claude-haiku-4-5"

SYSTEM_PROMPT = """
You are a travel planner. Return ONLY a JSON array of daily activities.

STRICT FORMAT - you must return exactly this structure:
[
    {
        "day": 1,
        "activities": ["Place Name 1", "Place Name 2", "Place Name 3"]
    },
    {
        "day": 2,
        "activities": ["Place Name 1", "Place Name 2", "Place Name 3"]
    }
]

RULES:
- activities must be a simple list of strings (place names only)
- no nested objects inside activities
- no extra fields like time, cost, description, location
- no trip_title, destination, duration or any other fields
- just day and activities
"""

def build_user_prompt(destination: str, days: int, budget: float, trip_style: str) -> str:
    return f"""
Plan a {days}-day trip to {destination}.
Budget: ${budget}
Travel style: {trip_style}

Return a JSON array with {days} objects.
Each object has "day" (number) and "activities" (list of 3-5 place name strings).
Nothing else.
"""

def add_user_message(messages: list, content: str):
    messages.append({"role": "user", "content": content})

def add_assistant_message(messages: list, content: str):
    messages.append({"role": "assistant", "content": content})

def generate_itinerary(destination: str, days: int, budget: float, trip_style: str) -> list[dict]:
    user_prompt = build_user_prompt(destination, days, budget, trip_style)

    messages = []
    add_user_message(messages, user_prompt)
    add_assistant_message(messages, "```json\n[")

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.3,
        system=SYSTEM_PROMPT,
        messages=messages,
        stop_sequences=["```"]
    )

    response_text = "[" + message.content[0].text

    try:
        itinerary = json.loads(response_text)
        return itinerary
    except json.JSONDecodeError:
        raise ValueError(f"Claude returned invalid JSON: {response_text}")