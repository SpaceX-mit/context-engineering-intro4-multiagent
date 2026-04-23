"""Test Agent for test coverage analysis."""

from pathlib import Path

from core.models import ReviewResult
from .tools import analyze_coverage, suggest_tests, analyze_test_needs, generate_test_template
from .prompts import SYSTEM_PROMPT


def create_test_agent():
    """
    Create and return the test agent instance.

    Returns:
        Configured PydanticAI Agent for test coverage
    """
    from pydantic_ai import Agent

    from providers import get_llm_model

    return Agent(
        get_llm_model(),
        deps_type=None,
        system_prompt=SYSTEM_PROMPT,
    )


# Lazy-loaded agent instance
_test_agent = None


def get_test_agent():
    """Get or create the test agent instance."""
    global _test_agent
    if _test_agent is None:
        _test_agent = create_test_agent()
    return _test_agent