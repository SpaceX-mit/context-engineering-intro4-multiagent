"""Coder Agent - Code generation and implementation."""

from __future__ import annotations
from typing import Optional, Tuple

from agent_framework.ollama import OllamaChatClient

from agents.base import BaseAgent, AgentConfig, AgentType


CODER_INSTRUCTIONS = '''You are the Coder Agent in the Multi-Agent Development System.

Your role is to write clean, working Python code that fulfills requirements.

## When Given a Task:

1. Understand the Spec - What needs to be built?
2. Write Complete Code - Full implementation, not snippets
3. Follow Best Practices - Type hints, docstrings, error handling
4. Execute and Verify - Run the code to ensure it works
5. Present Results - Show code and output

## Code Format

Write Python code in markdown blocks like this:
"""python
# filename.py
"""Module docstring."""

class ClassName:
    """Class docstring."""

    def method(self, param: str) -> str:
        """Method docstring."""
        return param
"""

## Execution

Always execute code to verify it works. Show:
1. The code written
2. Output from running it

## Quality Standards

- Use type hints on all functions
- Add docstrings for classes and public methods
- Handle errors gracefully
- Keep functions small and focused
- Use clear variable names

Be productive. Write code that works.'''


def create_coder_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Create a Coder agent."""
    config = AgentConfig(
        name="Coder",
        role="Code generation and implementation",
        instructions=CODER_INSTRUCTIONS,
        agent_type=AgentType.CODER,
        tools=["code_runner", "shell", "file_search"],
    )
    return BaseAgent(config, client)


def get_coder_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Get or create Coder agent."""
    return create_coder_agent(client, model)


async def write_code(agent: BaseAgent, spec: str) -> Tuple[str, str]:
    """Helper to write code from a spec."""
    response = await agent.run(f"Write Python code for: {spec}")

    # Extract code from markdown
    import re
    code_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
    code = code_match.group(1).strip() if code_match else ""

    return code, response