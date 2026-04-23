"""LLM provider configuration."""

from typing import Optional, TYPE_CHECKING

from settings import load_settings

if TYPE_CHECKING:
    from pydantic_ai import OpenAIModel


def get_llm_model() -> "OpenAIModel":
    """
    Get LLM model based on provider configuration.
    Supports OpenAI-compatible APIs using PydanticAI.

    Returns:
        Configured PydanticAI OpenAI model
    """
    try:
        from pydantic_ai.providers.openai import OpenAIProvider
        from pydantic_ai.models.openai import OpenAIModel

        settings = load_settings()

        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY is not set in .env file")

        provider = OpenAIProvider(
            base_url=settings.llm_base_url or "https://api.openai.com/v1",
            api_key=settings.llm_api_key,
        )

        return OpenAIModel(settings.llm_model, provider=provider)
    except ImportError:
        raise ImportError(
            "PydanticAI is required. Install with: pip install pydantic-ai"
        )


def get_llm_client():
    """
    Get LLM client based on provider configuration.
    Supports OpenAI-compatible APIs.

    Returns:
        Configured LLM client
    """
    settings = load_settings()

    if settings.llm_provider == "openai":
        try:
            from agent_framework.openai import OpenAIChatClient

            return OpenAIChatClient(model=settings.llm_model)
        except ImportError:
            # Fallback to direct API usage
            pass

    # Default: use OpenAI-compatible client
    try:
        from agent_framework.openai import OpenAIChatClient

        return OpenAIChatClient(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    except ImportError:
        # Final fallback for development without agent-framework
        return None


def get_model_info() -> dict:
    """Get information about current model configuration."""
    settings = load_settings()

    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "base_url": settings.llm_base_url,
    }