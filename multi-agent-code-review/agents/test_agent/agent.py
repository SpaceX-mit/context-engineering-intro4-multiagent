"""Test Agent - Test generation and coverage analysis."""

from __future__ import annotations
from typing import Optional, Dict, Any

from agent_framework.ollama import OllamaChatClient

from agents.base import BaseAgent, AgentConfig, AgentType


TESTER_INSTRUCTIONS = '''You are the Tester Agent in the Multi-Agent Development System.

Your role is to generate tests and analyze test coverage.

## When Given Code to Test:

1. Understand the Code - What does it do?
2. Identify Test Cases - Happy path, edge cases, errors
3. Write Tests - pytest format with clear assertions
4. Run Tests - Verify they pass
5. Report Coverage - What percentage is covered?

## Test Format

Write test code in markdown blocks like this:
"""python
import pytest

class TestClassName:
    def test_method_happy_path(self):
        obj = ClassName()
        result = obj.method(input_val)
        assert result == expected
"""

## Output Format

### Tests Written
- Test file
- Lines covered

### Test Results
PASSED: 5
FAILED: 0

### Coverage
- Functions: 80%
- Lines: 75%

Be thorough. Test edge cases, not just happy paths.'''


def create_tester_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Create a Tester agent."""
    config = AgentConfig(
        name="Tester",
        role="Test generation and coverage analysis",
        instructions=TESTER_INSTRUCTIONS,
        agent_type=AgentType.TESTER,
        tools=["code_runner", "shell"],
    )
    return BaseAgent(config, client)


def get_tester_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Get or create Tester agent."""
    return create_tester_agent(client, model)


async def generate_tests(agent: BaseAgent, code: str) -> Dict[str, Any]:
    """Generate tests for code and return results."""
    response = await agent.run(f"Generate pytest tests for:\n\n{code}")
    return {"tests_generated": True, "response": response}