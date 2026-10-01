import logging
from io import BytesIO

from gtts import gTTS

logger = logging.getLogger(__name__)


def synthesize_speech(text: str) -> bytes:
    if not text.strip():
        raise ValueError("Cannot synthesize speech from empty text")

    logger.info(f"Synthesizing speech for {len(text)} character(s) of text")
    buffer = BytesIO()
    tts = gTTS(text, lang="en")
    tts.write_to_fp(buffer)
    return buffer.getvalue()
