import logging
from sqlmodel import Session, select
from src.models.trip import Trip
from src.models.itinerary import Itinerary, ItineraryDay
from src.schemas.itinerary_schema import ItinerarySchema
from src.services.knowledge_service import KnowledgeService
from src.llm import get_llm_client
from src.llm.retry_handler import RetryHandler

logger = logging.getLogger(__name__)


class ItineraryService:
    def __init__(self):
        self.llm = get_llm_client()
        self.knowledge_service = KnowledgeService()
        self.retry_handler = RetryHandler(
            max_attempts=3,
            delay=1.0
        )

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

        knowledge_context = self._retrieve_knowledge_context(trip, session)

        itinerary_schema = self.retry_handler.execute(
            self.llm.generate_itinerary,
            destination=trip.destination,
            days=trip.days,
            budget=trip.budget,
            trip_style=trip.trip_style,
            knowledge_context=knowledge_context
        )

        logger.info(
            f"Successfully generated itinerary for "
            f"{trip.destination} using "
            f"{self.llm.get_provider_name()}/"
            f"{self.llm.get_model_name()}"
        )

        return self._save_itinerary(
            trip_id=trip.id,
            itinerary_schema=itinerary_schema,
            session=session
        )

    def _retrieve_knowledge_context(
        self,
        trip: Trip,
        session: Session
    ) -> list:

        query = f"{trip.destination} {trip.trip_style} travel tips"
        try:
            chunks = self.knowledge_service.search(query, session, top_k=3)
            return [chunk.content for chunk in chunks]
        except Exception:
            logger.exception(
                f"Knowledge base retrieval failed for trip {trip.id}, "
                f"continuing without retrieved context"
            )
            return []

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