"""Fixer Agent for automatic code fixes."""

from pathlib import Path

from pydantic_ai import Agent, RunContext

from providers import get_llm_model
from core.models import CodeIssue, ReviewResult
from .tools import fix_imports, fix_style_issues, verify_fix, apply_fixes
from .prompts import SYSTEM_PROMPT


def create_fixer_agent():
    """
    Create and return the fixer agent instance.

    Returns:
        Configured PydanticAI Agent for code fixing
    """
    from pydantic_ai import Agent

    from providers import get_llm_model

    return Agent(
        get_llm_model(),
        deps_type=None,
        system_prompt=SYSTEM_PROMPT,
    )


# Lazy-loaded agent instance
_fixer_agent = None


def get_fixer_agent():
    """Get or create the fixer agent instance."""
    global _fixer_agent
    if _fixer_agent is None:
        _fixer_agent = create_fixer_agent()
    return _fixer_agent