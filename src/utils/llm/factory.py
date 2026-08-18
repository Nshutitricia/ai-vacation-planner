import logging
from src.config import settings
from src.utils.llm.base import BaseLLM

logger = logging.getLogger(__name__)

def get_llm_client() -> BaseLLM:
    """
    Factory function that returns the correct LLM client
    based on the LLM_PROVIDER setting in .env.

    This is the only place in the codebase that knows
    which LLM provider is being used.
    """
    provider = settings.LLM_PROVIDER.lower()

    logger.info(f"Creating LLM client for provider: {provider}")

    if provider == "anthropic":
        from src.utils.llm.anthropic_llm import AnthropicLLM
        return AnthropicLLM()

    elif provider == "openai":
        raise NotImplementedError(
            "OpenAI provider not implemented yet. "
            "Set LLM_PROVIDER=anthropic in your .env"
        )

    elif provider == "gemini":
        raise NotImplementedError(
            "Gemini provider not implemented yet. "
            "Set LLM_PROVIDER=anthropic in your .env"
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported providers: anthropic"
        )