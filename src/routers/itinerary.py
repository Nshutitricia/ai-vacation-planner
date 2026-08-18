import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from src.database import get_session
from src.models.itinerary import ItineraryResponse, ItineraryCreate, Itinerary, ItineraryDay
from src.models.user import User
from src.utils.deps import get_current_user, get_owned_trip, fetch_owned_trip
from src.models.trip import Trip
from src.utils.background_tasks import log_itinerary_creation
from src.models.itinerary import ItineraryGenerate
from src.services.itinerary_service import ItineraryService
from src.models.itinerary import ActivityDetail

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/itinerary",
    tags=["itinerary"],
)

@router.post("", response_model=ItineraryResponse, status_code=201)
def create_itinerary(
    itinerary_data: ItineraryCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    trip = fetch_owned_trip(itinerary_data.trip_id, current_user, session)

    existing = session.exec(
        select(Itinerary).filter(Itinerary.trip_id == itinerary_data.trip_id)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Itinerary already exists")

    itinerary = Itinerary(
        trip_id=itinerary_data.trip_id,
        days=[day.model_dump() for day in itinerary_data.days]
    )
    session.add(itinerary)
    session.commit()
    session.refresh(itinerary)

    background_tasks.add_task(
        log_itinerary_creation,
        destination=trip.destination,
    )

    return ItineraryResponse(
        trip_id=itinerary.trip_id,
        days=[ItineraryDay(**day) for day in itinerary.days],
        message="Itinerary created successfully"
    )

@router.post("/generate", response_model=ItineraryResponse, status_code=201)
def generate_ai_itinerary(
    itinerary_data: ItineraryGenerate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    trip = fetch_owned_trip(itinerary_data.trip_id, current_user, session)

    try:
        service = ItineraryService()
        itinerary = service.generate(trip=trip, session=session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception(
            f"AI itinerary generation failed for trip {trip.id}"
        )
        raise HTTPException(
            status_code=500,
            detail="AI generation failed. Please try again later."
        )

    return ItineraryResponse(
        trip_id=itinerary.trip_id,
        days=[ItineraryDay(**day) for day in itinerary.days],
        message="Itinerary generated successfully by AI"
    )

@router.get("/{trip_id}", response_model=ItineraryResponse)
def get_itinerary(
    trip: Trip = Depends(get_owned_trip),
    session: Session = Depends(get_session)
):
    itinerary = session.exec(
        select(Itinerary).filter(Itinerary.trip_id == trip.id)
    ).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    days = []
    for day in itinerary.days:
        activities = []
        for activity in day.get("activities", []):
            if isinstance(activity, dict):
                activities.append(ActivityDetail(**activity))
            else:
                activities.append(activity)

        days.append(ItineraryDay(
            day=day.get("day"),
            theme=day.get("theme"),
            activities=activities
        ))

    return ItineraryResponse(
        trip_id=itinerary.trip_id,
        days=days,
        message="Itinerary retrieved successfully"
    )
