import logging
from src.config import settings
from src.llm.base import BaseLLM

logger = logging.getLogger(__name__)

def get_llm_client() -> BaseLLM:
    provider = settings.LLM_PROVIDER.lower()

    logger.info(f"Creating LLM client for provider: {provider}")

    if provider == "anthropic":
        from src.llm.anthropic_llm import AnthropicLLM
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