
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from src.database import get_session
from src.models.trip import TripResponse, TripCreate, Trip
from src.models.user import User
from src.utils.deps import get_current_user

from src.utils.background_tasks import log_trip_creation

router = APIRouter(
    prefix="/trips",
    tags=["trips"],
)

@router.post("", response_model=TripResponse, status_code=201)
def create_trip(
        trip_data: TripCreate,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    trip = Trip.model_validate(
        trip_data,
        update={"user_id": current_user.id}
    )
    session.add(trip)
    session.commit()
    session.refresh(trip)
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
    trips = session.exec(select(Trip).filter(Trip.user_id == current_user.id)).all()
    return trips

@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
        trip_id:int,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not trip.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return trip

@router.put("/{trip_id}", response_model=TripResponse)
def update_trip(
        trip_id:int,
        trip_data: TripCreate,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not trip.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    trip_dict = trip_data.model_dump()
    for key, value in trip_dict.items():
        setattr(trip, key, value)

    session.add(trip)
    session.commit()
    session.refresh(trip)
    return trip

@router.delete("/{trip_id}", status_code=204)
def delete_trip(
        trip_id:int,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not trip.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    session.delete(trip)
    session.commit()

