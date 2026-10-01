import logging
import os
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


@router.post("/plan", response_model=VoicePlanResponse, status_code=201)
async def plan_trip_from_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        transcribed_text, itinerary = voice_service.plan_trip_from_audio(
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

    return VoicePlanResponse(
        transcribed_text=transcribed_text,
        trip_id=itinerary.trip_id,
        days=[ItineraryDay(**day) for day in itinerary.days],
        message="Itinerary generated successfully from voice input"
    )
