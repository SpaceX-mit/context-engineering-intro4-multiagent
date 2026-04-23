"""AI Coder Agent - Main agent implementation."""

from typing import Optional
from pydantic_ai import Agent

from providers import get_llm_model
from .prompts import SYSTEM_PROMPT


# Lazy-loaded agent instance
_agent = None


def create_aicoder_agent() -> Agent:
    """
    Create and return the AI Coder agent instance.

    Returns:
        Configured PydanticAI Agent
    """
    return Agent(
        get_llm_model(),
        deps_type=None,
        system_prompt=SYSTEM_PROMPT,
    )


def get_aicoder_agent() -> Agent:
    """Get or create the AI Coder agent instance (lazy loading)."""
    global _agent
    if _agent is None:
        _agent = create_aicoder_agent()
    return _agent


async def run_aicoder(prompt: str, agent: Agent = None) -> str:
    """
    Run the AI Coder agent with a prompt.

    Args:
        prompt: User prompt/requirement
        agent: Optional agent instance (uses lazy singleton if not provided)

    Returns:
        Agent response as string
    """
    if agent is None:
        agent = get_aicoder_agent()

    result = await agent.run(prompt)
    return result.output if hasattr(result, "output") else str(result)


async def run_aicoder_streaming(prompt: str, agent: Agent = None):
    """
    Run the AI Coder agent with streaming response.

    Args:
        prompt: User prompt/requirement
        agent: Optional agent instance

    Yields:
        Chunks of the response
    """
    if agent is None:
        agent = get_aicoder_agent()

    async with agent.run_stream(prompt) as response:
        async for chunk in response.stream:
            yield chunk