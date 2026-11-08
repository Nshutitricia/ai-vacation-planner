from src.schemas.itinerary_schema import ItinerarySchema


def itinerary_to_text(itinerary: ItinerarySchema) -> str:
    """A readable version of the itinerary, for an LLM judge to read."""
    lines = [
        f"Destination: {itinerary.destination}",
        f"Days: {itinerary.total_days}",
        f"Estimated total cost: {itinerary.estimated_total_cost}",
    ]
    for day in itinerary.days:
        lines.append(f"\nDay {day.day}: {day.theme}")
        for a in day.activities:
            lines.append(f"- {a.name} ({a.estimated_cost}): {a.description}")
    return "\n".join(lines)


def request_to_text(destination: str, days: int, budget: float, trip_style: str,
                    preferences: str | None = None) -> str:
    text = (
        f"Plan a {days}-day {trip_style} trip to {destination} "
        f"with a total budget of ${budget:g}."
    )
    if preferences:
        text += f" The traveler also asked: {preferences}."
    return text
