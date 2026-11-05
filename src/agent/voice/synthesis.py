import logging
from io import BytesIO

from gtts import gTTS

logger = logging.getLogger(__name__)

MAX_CHARS = 600
SENTENCE_BOUNDARIES = (". ", "! ", "? ")


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

    # One extra character, so a sentence that ends exactly at max_chars
    # (terminator on the last allowed index, space just past it) still counts.
    window = text[:max_chars + 1]
    cut = max(window.rfind(boundary) for boundary in SENTENCE_BOUNDARIES)
    if cut != -1:
        logger.info(f"Truncated narration from {len(text)} to {cut + 1} character(s)")
        return window[:cut + 1]

    logger.info(f"Truncated narration from {len(text)} to {max_chars} character(s)")
    return text[:max_chars]
