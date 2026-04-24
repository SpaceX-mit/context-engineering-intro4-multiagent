"""Base classes for all agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from agent_framework import Agent, Message
from agent_framework.ollama import OllamaChatClient

from skills import Context, Skill, get_registry


class AgentType(Enum):
    """Agent type enumeration."""
    COORDINATOR = "coordinator"
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    LINTER = "linter"
    FIXER = "fixer"
    TESTER = "tester"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    role: str
    instructions: str
    agent_type: AgentType
    model: str = "llama3.2"
    tools: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class AgentResult:
    """Result from agent execution."""
    status: str  # success, error, pending
    agent: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    next_action: Optional[str] = None
    output: str = ""

    def to_json(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "agent": self.agent,
            "results": self.results,
            "next_action": self.next_action,
            "output": self.output,
        }


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(
        self,
        config: AgentConfig,
        client: Optional[OllamaChatClient] = None,
        skills: Optional[List[Skill]] = None,
    ):
        self.config = config
        self.client = client or OllamaChatClient(model=config.model)
        self.skills = skills or []
        self._skill_registry = get_registry()
        self._agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Create the underlying agent_framework Agent."""
        skill_tools = [
            self._skill_registry.get(t)
            for t in self.config.tools
            if self._skill_registry.get(t)
        ]
        active_tools = [t for t in skill_tools if t is not None]

        return Agent(
            client=self.client,
            name=self.config.name,
            instructions=self.config.instructions,
            tools=active_tools if active_tools else None,
        )

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> str:
        return self.config.role

    async def run(self, prompt: str, context: Optional[Context] = None) -> str:
        """Run the agent with a prompt."""
        result = await self._agent.run(prompt)
        return result.text if hasattr(result, "text") else str(result)

    async def run_streaming(self, prompt: str):
        """Run with streaming output."""
        async for chunk in self._agent.run(prompt, stream=True):
            if chunk.text:
                yield chunk.text

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "name": self.name,
            "type": self.config.agent_type.value,
            "status": "active",
        }

    async def execute_skill(self, skill_name: str, context: Context, **kwargs):
        """Execute a skill by name."""
        skill = self._skill_registry.get(skill_name)
        if not skill:
            return AgentResult(
                status="error",
                agent=self.name,
                results=[],
                next_action=None,
                output=f"Skill not found: {skill_name}"
            )
        result = await skill.execute_with_timeout(context, **kwargs)
        return result