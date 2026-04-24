"""Planner Agent - Project planning and task decomposition."""

from __future__ import annotations
from typing import Optional, Dict, List, Any

from agent_framework.ollama import OllamaChatClient

from agents.base import BaseAgent, AgentConfig, AgentType


PLANNER_INSTRUCTIONS = """You are the Planner Agent in the Multi-Agent Development System.

Your role is to break down user requirements into clear, actionable implementation steps.

## When Given a Requirement:

1. **Understand the Goal** - What does the user want to build?
2. **Identify Components** - What files, modules, classes are needed?
3. **Create Step-by-Step Plan** - Numbered steps in execution order
4. **Consider Dependencies** - What must happen first?
5. **Estimate Complexity** - How difficult is each step?

## Output Format

### Analysis
[Brief understanding of what needs to be built]

### Plan
1. [Step 1 - clear action]
2. [Step 2 - clear action]
3. ...

### Files to Create
- `filename1.py` - [purpose]
- `filename2.py` - [purpose]

### Dependencies
- [External libraries or systems needed]

### Estimated Complexity
- Low / Medium / High

Be practical. Focus on the minimum viable approach.
Do not over-engineer. Start simple, add complexity only if needed."""


def create_planner_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Create a Planner agent."""
    config = AgentConfig(
        name="Planner",
        role="Project planning and task decomposition",
        instructions=PLANNER_INSTRUCTIONS,
        agent_type=AgentType.PLANNER,
        tools=["file_search"],
    )
    return BaseAgent(config, client)


def get_planner_agent(
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2"
) -> BaseAgent:
    """Get or create Planner agent."""
    return create_planner_agent(client, model)