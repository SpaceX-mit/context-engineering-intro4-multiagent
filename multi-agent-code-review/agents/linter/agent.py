"""Linter Agent for code style and formatting analysis.

This module provides the Linter Agent for code review.
The agent uses PydanticAI for LLM interactions.
"""

from pathlib import Path
from typing import Optional

from core.models import ReviewResult
from .tools import lint_file, check_unused_imports, check_style, analyze_lint_result
from .prompts import SYSTEM_PROMPT


def create_linter_agent():
    """
    Create and return the linter agent instance.

    Returns:
        Configured PydanticAI Agent for linting
    """
    from pydantic_ai import Agent

    from providers import get_llm_model

    return Agent(
        get_llm_model(),
        deps_type=None,
        system_prompt=SYSTEM_PROMPT,
    )


# Lazy-loaded agent instance
_linter_agent = None


def get_linter_agent():
    """Get or create the linter agent instance."""
    global _linter_agent
    if _linter_agent is None:
        _linter_agent = create_linter_agent()
    return _linter_agent


# For backward compatibility
linter_agent = None