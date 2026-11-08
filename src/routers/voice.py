import logging
import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from src.database import get_session
from src.models.itinerary import ItineraryDay
from src.models.user import User
from src.models.voice import VoicePlanResponse
from src.services.voice_service import VoiceService
from src.utils.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/voice",
    tags=["voice"],
)

voice_service = VoiceService()


# Plain `def`, not `async def`: transcription, Claude calls and DB work all block,
# so FastAPI runs this in its threadpool and the event loop stays free.
@router.post("/plan", response_model=VoicePlanResponse, status_code=201)
def plan_trip_from_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    try:
        result = voice_service.plan_trip_from_audio(
            tmp_path, current_user, session
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Voice itinerary generation failed")
        raise HTTPException(
            status_code=500,
            detail="AI generation failed. Please try again later."
        )
    finally:
        os.unlink(tmp_path)

    itinerary = result.itinerary
    message = "Itinerary generated successfully from voice input"
    if result.inferred_fields:
        message += (
            f" (assumed because you didn't mention them: "
            f"{', '.join(result.inferred_fields)})"
        )

    return VoicePlanResponse(
        transcribed_text=result.transcribed_text,
        trip_id=itinerary.trip_id,
        trip_details=result.trip,
        preferences=result.preferences,
        inferred_fields=result.inferred_fields,
        days=[ItineraryDay(**day) for day in itinerary.days],
        message=message
    )
