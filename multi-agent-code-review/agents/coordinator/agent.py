"""Coordinator Agent for multi-agent code review orchestration."""

from pathlib import Path

from pydantic_ai import Agent, RunContext

from providers import get_llm_model
from core.models import ReviewRequest, ReviewReport
from .tools import orchestrate_review, aggregate_results, generate_report
from .prompts import SYSTEM_PROMPT


def create_coordinator_agent():
    """
    Create and return the coordinator agent instance.

    Returns:
        Configured PydanticAI Agent for coordination
    """
    from pydantic_ai import Agent

    from providers import get_llm_model

    return Agent(
        get_llm_model(),
        deps_type=None,
        system_prompt=SYSTEM_PROMPT,
    )


# Lazy-loaded agent instance
_coordinator_agent = None


def get_coordinator_agent():
    """Get or create the coordinator agent instance."""
    global _coordinator_agent
    if _coordinator_agent is None:
        _coordinator_agent = create_coordinator_agent()
    return _coordinator_agent