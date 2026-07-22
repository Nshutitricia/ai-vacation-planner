import time
import logging
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

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
        Retries on ValueError up to max_attempts times.
        Raises the last error if all attempts fail.
        """
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info(f"Attempt {attempt} of {self.max_attempts}")
                result = func(*args, **kwargs)
                logger.info(f"Attempt {attempt} succeeded")
                return result

            except ValueError as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt} failed: {str(e)}"
                )

                if attempt < self.max_attempts:
                    logger.info(f"Retrying in {self.delay} seconds...")
                    time.sleep(self.delay)
                else:
                    logger.error(
                        f"All {self.max_attempts} attempts failed"
                    )

        raise ValueError(
            f"Failed after {self.max_attempts} attempts. "
            f"Last error: {str(last_error)}"
        )