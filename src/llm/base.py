from abc import ABC, abstractmethod
from src.schemas.itinerary_schema import ItinerarySchema

class BaseLLM(ABC):

    @abstractmethod
    def generate_itinerary(
        self,
        destination: str,
        days: int,
        budget: float,
        trip_style: str,
        knowledge_context: list = None
    ) -> ItinerarySchema:


        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Return the name of the model being used.
        e.g. 'claude-haiku-4-5', 'gpt-4o-mini'
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Return the name of the provider.
        e.g. 'anthropic', 'openai', 'gemini'
        """
        pass