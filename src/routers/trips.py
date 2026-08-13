
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session
from src.database import get_session
from src.models.trip import TripResponse, TripCreate, Trip
from src.models.user import User
from src.utils.deps import get_current_user, get_owned_trip

from src.utils.background_tasks import log_trip_creation

from src.services.trip_service import TripService

router = APIRouter(
    prefix="/trips",
    tags=["trips"],
)

trip_service = TripService()

@router.post("", response_model=TripResponse, status_code=201)
def create_trip(
        trip_data: TripCreate,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    trip = trip_service.create(trip_data, user_id=current_user.id, session=session)
    background_tasks.add_task(
        log_trip_creation,
        username = current_user.username,
        destination = trip.destination,
    )
    return trip

@router.get("", response_model=list[TripResponse])
def get_trips(
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    return trip_service.list_for_user(current_user.id, session)

@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(trip: Trip = Depends(get_owned_trip)):
    return trip

@router.put("/{trip_id}", response_model=TripResponse)
def update_trip(
        trip_data: TripCreate,
        trip: Trip = Depends(get_owned_trip),
        session: Session = Depends(get_session)
):
    return trip_service.update(trip, trip_data, session)

@router.delete("/{trip_id}", status_code=204)
def delete_trip(
        trip: Trip = Depends(get_owned_trip),
        session: Session = Depends(get_session)
):
    trip_service.delete(trip, session)
