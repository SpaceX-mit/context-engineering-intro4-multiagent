"""Coder Agent module for code generation."""

from .agent import (
    create_coder_agent,
    get_coder_agent,
    get_coder_tools,
    create_code,
    validate_and_format,
    run_coder_sync,
)
from .tools import (
    validate_code,
    suggest_tests,
    format_code,
    analyze_code_structure,
)
from .prompts import (
    SYSTEM_PROMPT,
    CODE_GENERATION_PROMPT,
    generate_code_prompt,
    fix_code_prompt,
    explain_code_prompt,
)

# Lazy-loaded agent instance
_coder_agent = None


def get_coder() -> "Agent":
    """Get or create the coder agent instance (lazy loading)."""
    global _coder_agent
    if _coder_agent is None:
        _coder_agent = create_coder_agent()
    return _coder_agent


def get_coder_lazy():
    """Get coder agent, creating only when needed."""
    return get_coder()


# For backward compatibility, but don't create agent at import time
def _get_coder_placeholder():
    """Placeholder that creates agent lazily."""
    return get_coder()

# Don't create agent at module load - create lazily
coder_agent = None  # Will be None until first use

__all__ = [
    "create_coder_agent",
    "get_coder_agent",
    "get_coder",
    "get_coder_tools",
    "create_code",
    "validate_and_format",
    "run_coder_sync",
    "validate_code",
    "suggest_tests",
    "format_code",
    "analyze_code_structure",
    "SYSTEM_PROMPT",
    "CODE_GENERATION_PROMPT",
    "generate_code_prompt",
    "fix_code_prompt",
    "explain_code_prompt",
    "coder_agent",
]