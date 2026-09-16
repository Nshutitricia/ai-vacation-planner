from sqlmodel import Session, select
from src.models.trip import Trip, TripCreate
from src.models.itinerary import Itinerary


class TripService:
    def create(self, trip_data: TripCreate, user_id: int, session: Session) -> Trip:
        trip = Trip.model_validate(trip_data, update={"user_id": user_id})
        session.add(trip)
        session.commit()
        session.refresh(trip)
        return trip

    def list_for_user(self, user_id: int, session: Session) -> list[Trip]:
        return session.exec(
            select(Trip).filter(Trip.user_id == user_id)
        ).all()

    def update(self, trip: Trip, trip_data: TripCreate, session: Session) -> Trip:
        for key, value in trip_data.model_dump().items():
            setattr(trip, key, value)
        session.add(trip)
        session.commit()
        session.refresh(trip)
        return trip

    def delete(self, trip: Trip, session: Session) -> None:
        itinerary = session.exec(
            select(Itinerary).filter(Itinerary.trip_id == trip.id)
        ).first()
        if itinerary:
            session.delete(itinerary)
        session.delete(trip)
        session.commit()
