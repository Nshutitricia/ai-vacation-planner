from langchain_core.tools import tool

DAILY_COST_RANGES = {
    "budget": (30, 60),
    "luxury": (250, 600),
    "adventure": (60, 150),
    "cultural": (70, 160),
    "family": (100, 220),
}

DEFAULT_RANGE = (60, 150)


@tool
def estimate_trip_cost(trip_style: str, days: int) -> str:
    low, high = DAILY_COST_RANGES.get(trip_style.lower(), DEFAULT_RANGE)
    total_low = low * days
    total_high = high * days
    return (
        f"Estimated cost for a {days}-day {trip_style} trip: "
        f"${total_low}-${total_high} total "
        f"(roughly ${low}-${high} per day for accommodation, food, "
        f"and activities combined). This is a general estimate, not "
        f"real-time destination-specific pricing."
    )
