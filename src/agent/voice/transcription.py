import logging

from faster_whisper import WhisperModel

from src.config import settings

logger = logging.getLogger(__name__)

_model: WhisperModel = None


def _get_model() -> WhisperModel:

    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
        _model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe_audio(file_path: str) -> str:

    model = _get_model()
    segments, info = model.transcribe(file_path)
    text = " ".join(segment.text for segment in segments).strip()

    if not text:
        raise ValueError("Could not detect any speech in the audio")

    logger.info(f"Transcribed audio (language={info.language}): {text}")
    return text
