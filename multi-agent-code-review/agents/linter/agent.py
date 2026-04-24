"""Linter Agent - Code style checking and formatting."""

from __future__ import annotations
from typing import Optional

from agent_framework.ollama import OllamaChatClient

from agents.base import BaseAgent, AgentConfig, AgentType


LINTER_INSTRUCTIONS = '''You are the Linter Agent in the Multi-Agent Development System.

Your role is to check code for style issues, formatting, and auto-fixable problems.

## When Given Code to Lint:

1. Syntax Check - Is the code syntactically correct?
2. Style Issues - PEP8 violations, naming conventions
3. Formatting - Indentation, whitespace, line length
4. Imports - Unused imports, missing imports
5. Auto-fixable - What can be automatically fixed?

## Output Format

### Style Issues
Line | Issue | Auto-fix
23 | Line too long | Yes
45 | Unused import | Yes

### Summary
- Issues found: N
- Auto-fixable: N
- Needs manual review: N

Be precise. Provide exact line numbers and corrections.'''


def create_linter_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Create a Linter agent."""
    config = AgentConfig(
        name="Linter",
        role="Code style checking and formatting",
        instructions=LINTER_INSTRUCTIONS,
        agent_type=AgentType.LINTER,
        tools=["linter", "file_search"],
    )
    return BaseAgent(config, client)


def get_linter_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Get or create Linter agent."""
    return create_linter_agent(client, model)