import time
import logging
from typing import Callable, TypeVar

from anthropic import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_EXCEPTIONS = (
    ValueError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)


class RetryHandler:
    """
    Responsible for retrying failed LLM calls.
    """

    def __init__(self, max_attempts: int = 3, delay: float = 1.0):
        """
        max_attempts → how many times to try before giving up
        delay        → seconds to wait between attempts
        """
        self.max_attempts = max_attempts
        self.delay = delay

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with retry logic.
        Retries on RETRYABLE_EXCEPTIONS up to max_attempts times.
        Raises the last error if all attempts fail.
        """
        last_error = None

        for attempt in range(self.max_attempts):
            attempt_number = attempt + 1
            try:
                logger.info(f"Attempt {attempt_number} of {self.max_attempts}")
                result = func(*args, **kwargs)
                logger.info(f"Attempt {attempt_number} succeeded")
                return result

            except RETRYABLE_EXCEPTIONS as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt_number} failed: {str(e)}"
                )

                if attempt_number < self.max_attempts:
                    logger.info(f"Retrying in {self.delay} seconds...")
                    time.sleep(self.delay)
                else:
                    logger.error(
                        f"All {self.max_attempts} attempts failed"
                    )

        raise last_error