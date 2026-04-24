"""Fixer Agent - Problem repair and code optimization."""

from __future__ import annotations
from typing import Optional, List, Dict, Any

from agent_framework.ollama import OllamaChatClient

from agents.base import BaseAgent, AgentConfig, AgentType


FIXER_INSTRUCTIONS = '''You are the Fixer Agent in the Multi-Agent Development System.

Your role is to automatically fix code issues and optimize code quality.

## When Given Issues to Fix:

1. Understand the Issue - What needs to be fixed?
2. Apply Fix - Make the minimal change needed
3. Verify - Ensure fix does not break functionality
4. Optimize - Improve code where appropriate

## Issue Types

Type | Action
Linter | Auto-fix style issues
Reviewer | Apply suggested changes
Logic | Refactor for correctness
Security | Apply security best practices

## Output Format

### Fixes Applied
Original | Fixed | Reason
x=1 | x = 1 | PEP8 spacing

### Verification
How the fix was verified

Be careful. Only fix what was requested. Do not make unnecessary changes.'''


def create_fixer_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Create a Fixer agent."""
    config = AgentConfig(
        name="Fixer",
        role="Problem repair and code optimization",
        instructions=FIXER_INSTRUCTIONS,
        agent_type=AgentType.FIXER,
        tools=["code_runner", "shell", "file_search"],
    )
    return BaseAgent(config, client)


def get_fixer_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Get or create Fixer agent."""
    return create_fixer_agent(client, model)


async def fix_code(agent: BaseAgent, code: str, issues: List[str]) -> Dict[str, Any]:
    """Fix code issues and return results."""
    response = await agent.run(f"Fix these issues in the code:\n\n{issues}\n\nCode:\n{code}")
    return {"fixed": True, "response": response}