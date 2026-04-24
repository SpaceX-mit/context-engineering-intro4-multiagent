"""Coordinator Agent - Task decomposition and coordination."""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid

from agent_framework import Agent
from agent_framework.ollama import OllamaChatClient

from agents.base import BaseAgent, AgentConfig, AgentType, AgentResult


COORDINATOR_INSTRUCTIONS = """You are the Coordinator Agent in the Multi-Agent Development System.

Your role is to:
1. **Parse Requirements** - Understand what the user wants
2. **Decompose Tasks** - Break down into smaller, manageable tasks
3. **Delegate** - Route tasks to appropriate specialist agents
4. **Coordinate** - Manage the workflow between agents
5. **Aggregate** - Collect results and present to user

## Available Specialist Agents

| Agent | Role | Use When |
|-------|------|----------|
| Planner | Project planning, task breakdown | Need implementation strategy |
| Coder | Code generation, implementation | Need code written |
| Reviewer | Quality assessment, logic review | Need code reviewed |
| Linter | Style checking, formatting | Need code formatted |
| Tester | Test generation, coverage | Need tests created |
| Fixer | Problem repair, optimization | Need issues fixed |

## Output Format

Your output MUST follow this structure:
- Start with **Analysis**: What you understand from the request
- Then **Plan**: Task decomposition with agent assignments
- Use numbered lists for clarity

Be decisive. When a task is clear, delegate immediately.
Never do specialized work yourself - always route to the right agent."""


@dataclass
class Task:
    """A task in the system."""
    id: str
    description: str
    assigned_to: Optional[str] = None
    status: str = "pending"
    result: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)


def create_coordinator_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Create a Coordinator agent."""
    config = AgentConfig(
        name="Coordinator",
        role="Task decomposition and workflow coordination",
        instructions=COORDINATOR_INSTRUCTIONS,
        agent_type=AgentType.COORDINATOR,
        tools=["file_search"],
    )
    return BaseAgent(config, client)


def get_coordinator_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Get or create Coordinator agent."""
    return create_coordinator_agent(client, model)