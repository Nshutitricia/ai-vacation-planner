import logging
import re
import unicodedata

from src.guardrails.errors import InputRejectedError

logger = logging.getLogger(__name__)


INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|preceding|all|your|the)\b.{0,30}\b(instructions?|prompts?|rules|guidelines|messages)\b",
    r"\b(reveal|show|print|repeat|display|leak)\b.{0,25}\b(system|initial|hidden|original)\b.{0,10}\b(prompt|instructions?)\b",
    r"\bsystem prompt\b",
    r"\byou are now (a|an|the)\b",
    r"\bpretend (to be|you are|you're)\b",
    r"\b(developer|debug|admin) mode\b",
    r"\bjailbreak\b",
    r"\bnew instructions?:",
    r"</?\s*(system|assistant|human|user)\s*>",
    r"\[/?\s*(inst|system)\s*\]",
]


UNSUPPORTED_ACTION_PATTERNS = [
    r"\b(book|reserve|purchase|buy)\b.{0,30}\b(flights?|hotels?|tickets?|rooms?|tours?|cars?)\b",
    r"\b(pay|charge|transfer|send)\b.{0,20}\b(money|payment|card|funds|e-?mail|message)\b",
    r"\bdelete\b.{0,15}\b(account|trips?|data)\b",
]

PLACE_NAME_PATTERN = re.compile(r"^[\w\s,.'()\-]+$", re.UNICODE)
STYLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z \-]*$")

_INVISIBLE = dict.fromkeys(
    [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD], None
)

UNSUPPORTED_MESSAGE = (
    "I can only plan itineraries. I can't book, pay for, or contact "
    "anyone on your behalf."
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_INVISIBLE)
    return re.sub(r"\s+", " ", text).strip().lower()


def check_injection(text: str, field: str = "text") -> None:
    normalized = _normalize(text)
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            logger.warning(f"Rejected possible prompt injection in {field}")
            raise InputRejectedError(
                f"The {field} contains instructions that can't be accepted."
            )


def check_unsupported_action(text: str, field: str = "text") -> None:
    normalized = _normalize(text)
    for pattern in UNSUPPORTED_ACTION_PATTERNS:
        if re.search(pattern, normalized):
            logger.warning(f"Rejected unsupported action request in {field}")
            raise InputRejectedError(UNSUPPORTED_MESSAGE)


def validate_place_name(value: str, field: str = "destination") -> str:
    if not PLACE_NAME_PATTERN.match(value):
        raise InputRejectedError(
            f"The {field} may only contain letters, spaces and basic punctuation."
        )
    check_injection(value, field)
    return value


def validate_trip_style(value: str) -> str:
    if not STYLE_PATTERN.match(value):
        raise InputRejectedError(
            "The trip style may only contain letters, spaces and hyphens."
        )
    check_injection(value, "trip style")
    return value


def validate_free_text(value: str, field: str = "text", max_length: int = 1000) -> str:
    if len(value) > max_length:
        raise InputRejectedError(f"The {field} is too long.")
    check_injection(value, field)
    check_unsupported_action(value, field)
    return value
