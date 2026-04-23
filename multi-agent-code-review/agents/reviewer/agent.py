"""Reviewer Agent for code quality assessment."""

from pathlib import Path

from core.models import ReviewResult
from .tools import (
    analyze_complexity,
    detect_security_issues,
    assess_maintainability,
    review_file,
)
from .prompts import SYSTEM_PROMPT


def create_reviewer_agent():
    """
    Create and return the reviewer agent instance.

    Returns:
        Configured PydanticAI Agent for code review
    """
    from pydantic_ai import Agent

    from providers import get_llm_model

    return Agent(
        get_llm_model(),
        deps_type=None,
        system_prompt=SYSTEM_PROMPT,
    )


# Lazy-loaded agent instance
_reviewer_agent = None


def get_reviewer_agent():
    """Get or create the reviewer agent instance."""
    global _reviewer_agent
    if _reviewer_agent is None:
        _reviewer_agent = create_reviewer_agent()
    return _reviewer_agent