import logging
from io import BytesIO

from gtts import gTTS

logger = logging.getLogger(__name__)

MAX_CHARS = 600


def synthesize_speech(text: str) -> bytes:
    if not text.strip():
        raise ValueError("Cannot synthesize speech from empty text")

    text = _truncate(text, MAX_CHARS)

    logger.info(f"Synthesizing speech for {len(text)} character(s) of text")
    buffer = BytesIO()
    tts = gTTS(text, lang="en")
    tts.write_to_fp(buffer)
    return buffer.getvalue()


def _truncate(text: str, max_chars: int) -> str:

    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    for boundary in (". ", "! ", "? "):
        cut = truncated.rfind(boundary)
        if cut != -1:
            logger.info(f"Truncated narration from {len(text)} to {cut + 1} character(s)")
            return truncated[:cut + 1]

    logger.info(f"Truncated narration from {len(text)} to {max_chars} character(s)")
    return truncated
