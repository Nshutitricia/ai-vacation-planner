import logging
import re

from src.guardrails.errors import OutputGuardError
from src.models.trip import Trip
from src.schemas.itinerary_schema import ItinerarySchema

logger = logging.getLogger(__name__)


MAX_BUDGET_RATIO = 2.0


def find_problems(itinerary: ItinerarySchema, trip: Trip) -> list[str]:
    problems = []

    if not _destinations_match(itinerary.destination, trip.destination):
        problems.append(
            f"destination '{itinerary.destination}' does not match "
            f"the trip's '{trip.destination}'"
        )

    if itinerary.total_days != trip.days or len(itinerary.days) != trip.days:
        problems.append(
            f"expected {trip.days} day(s), got {len(itinerary.days)}"
        )

    numbers = [day.day for day in itinerary.days]
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append(f"day numbers are not 1..N in order: {numbers}")

    cost = _first_amount(itinerary.estimated_total_cost)
    if cost is not None and cost > trip.budget * MAX_BUDGET_RATIO:
        problems.append(
            f"estimated cost {cost:g} is more than {MAX_BUDGET_RATIO:g}x "
            f"the budget of {trip.budget:g}"
        )

    return problems


def validate_itinerary(itinerary: ItinerarySchema, trip: Trip) -> None:
    problems = find_problems(itinerary, trip)
    if problems:
        logger.warning(f"Output guard rejected itinerary: {problems}")
        raise OutputGuardError("; ".join(problems))


def _destinations_match(generated: str, requested: str) -> bool:
    generated, requested = generated.strip().lower(), requested.strip().lower()
    return requested in generated or generated in requested


def _first_amount(text: str) -> float | None:

    match = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group().replace(",", ""))
