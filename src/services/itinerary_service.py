import logging
from sqlmodel import Session, select
from src.models.trip import Trip
from src.models.itinerary import Itinerary, ItineraryDay
from src.schemas.itinerary_schema import ItinerarySchema
from src.agent.graph import run_agent
from src.agent.voice.narration import narrate_itinerary

logger = logging.getLogger(__name__)


class ItineraryService:
    def generate(
        self,
        trip: Trip,
        session: Session
    ) -> Itinerary:
        logger.info(
            f"Starting itinerary generation for "
            f"trip {trip.id} to {trip.destination}"
        )

        self._check_existing_itinerary(trip.id, session)

        user_request = self._build_user_request(trip)
        itinerary_schema = run_agent(user_request, session)

        logger.info(
            f"Successfully generated itinerary for {trip.destination} via agent"
        )

        return self._save_itinerary(
            trip_id=trip.id,
            itinerary_schema=itinerary_schema,
            session=session
        )

    def build_narration(self, itinerary: Itinerary) -> str:

        raw_summary = self._build_raw_summary(itinerary)
        try:
            return narrate_itinerary(raw_summary)
        except ValueError:
            logger.warning(
                "Falling back to plain template summary (Option A) for "
                f"trip {itinerary.trip_id}"
            )
            return raw_summary

    def _build_raw_summary(self, itinerary: Itinerary) -> str:
        parts = []
        for day in itinerary.days:
            parts.append(f"Day {day.get('day')}: {day.get('theme')}.")
            for activity in day.get("activities", []):
                if isinstance(activity, dict):
                    name = activity.get("name", "")
                    description = activity.get("description", "")
                    cost = activity.get("estimated_cost", "")
                    parts.append(f"{name}. {description} Estimated cost: {cost}.")
                else:
                    parts.append(str(activity))
        return " ".join(parts)

    def _build_user_request(self, trip: Trip) -> str:
        return (
            f"Plan a {trip.days}-day trip to {trip.destination} with a "
            f"total budget of ${trip.budget}, in a {trip.trip_style} "
            f"style. Include weather-friendly activities, and use "
            f"relevant local travel knowledge where it's genuinely "
            f"helpful."
        )

    def _check_existing_itinerary(
        self,
        trip_id: int,
        session: Session
    ) -> None:

        existing = session.exec(
            select(Itinerary).filter(
                Itinerary.trip_id == trip_id
            )
        ).first()

        if existing:
            raise ValueError(
                f"Itinerary already exists for trip {trip_id}"
            )

    def _save_itinerary(
        self,
        trip_id: int,
        itinerary_schema: ItinerarySchema,
        session: Session
    ) -> Itinerary:
        days_data = [
            {
                "day": day.day,
                "theme": day.theme,
                "activities": [
                    {
                        "name": activity.name,
                        "description": activity.description,
                        "estimated_cost": activity.estimated_cost
                    }
                    for activity in day.activities
                ]
            }
            for day in itinerary_schema.days
        ]

        itinerary = Itinerary(
            trip_id=trip_id,
            days=days_data
        )

        session.add(itinerary)
        session.commit()
        session.refresh(itinerary)

        logger.info(
            f"Saved itinerary for trip {trip_id} "
            f"with {len(days_data)} days"
        )

        return itinerary