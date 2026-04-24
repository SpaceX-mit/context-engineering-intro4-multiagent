"""Reviewer Agent - Code quality assessment and logic review."""

from __future__ import annotations
from typing import Optional, Dict, Any

from agent_framework.ollama import OllamaChatClient

from agents.base import BaseAgent, AgentConfig, AgentType


REVIEWER_INSTRUCTIONS = '''You are the Reviewer Agent in the Multi-Agent Development System.

Your role is to check code for issues and provide quality assessment.

## When Given Code to Review:

1. Logic Check - Are there any logical errors?
2. Security Scan - Are there security vulnerabilities?
3. Performance - Any performance issues?
4. Edge Cases - Are boundary conditions handled?
5. Maintainability - Is code easy to understand and modify?

## Output Format

### Issues Found
Severity | Location | Issue | Suggestion
HIGH | line 42 | Null check missing | Add if x is None check

### Suggestions
- Suggestion 1
- Suggestion 2

### Overall Assessment
Good/Poor - Brief summary with score 1-10

If no issues found: "Code looks good!"

Be thorough. Catching issues early saves time later.'''


def create_reviewer_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Create a Reviewer agent."""
    config = AgentConfig(
        name="Reviewer",
        role="Code quality assessment and logic review",
        instructions=REVIEWER_INSTRUCTIONS,
        agent_type=AgentType.REVIEWER,
        tools=["linter", "file_search"],
    )
    return BaseAgent(config, client)


def get_reviewer_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Get or create Reviewer agent."""
    return create_reviewer_agent(client, model)


async def review_code(agent: BaseAgent, code: str) -> Dict[str, Any]:
    """Review code and return structured results."""
    response = await agent.run(f"Review this code:\n\n{code}")
    return {
        "review_text": response,
        "issues_found": 0,
        "severity": "none",
    }