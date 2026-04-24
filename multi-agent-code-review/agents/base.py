"""Base classes for all agents."""

from __future__ import annotations

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agent_framework import Agent, Message
from agent_framework.ollama import OllamaChatClient

from skills import Context, Skill, get_registry
from core.registry import AgentStatus


class AgentType(Enum):
    """Agent type enumeration."""
    COORDINATOR = "coordinator"
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    LINTER = "linter"
    FIXER = "fixer"
    TESTER = "tester"


class AgentLifecycleState(Enum):
    """Agent lifecycle states based on PRD.md Section 3.2."""
    PENDING = "pending"           # Waiting to initialize
    INIT = "init"                # Initializing
    RUNNING = "running"           # Actively executing
    WAITING = "waiting"           # Waiting for other agents
    COMPLETED = "completed"        # Finished successfully
    ERRORED = "errored"           # Encountered an error
    INTERRUPTED = "interrupted"   # Interrupted by user
    CLOSED = "closed"            # Shutdown


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
    """
    Base class for all agents in the system.

    Implements the lifecycle state machine from PRD.md Section 3.2:
    PENDING → INIT → RUNNING → (COMPLETED | ERRORED | INTERRUPTED) → CLOSED
    """

    # Valid state transitions
    VALID_TRANSITIONS: Dict[AgentLifecycleState, List[AgentLifecycleState]] = {
        AgentLifecycleState.PENDING: [AgentLifecycleState.INIT],
        AgentLifecycleState.INIT: [AgentLifecycleState.RUNNING, AgentLifecycleState.ERRORED],
        AgentLifecycleState.RUNNING: [
            AgentLifecycleState.COMPLETED,
            AgentLifecycleState.ERRORED,
            AgentLifecycleState.INTERRUPTED,
            AgentLifecycleState.WAITING,
        ],
        AgentLifecycleState.WAITING: [
            AgentLifecycleState.RUNNING,
            AgentLifecycleState.ERRORED,
            AgentLifecycleState.INTERRUPTED,
        ],
        AgentLifecycleState.COMPLETED: [AgentLifecycleState.CLOSED],
        AgentLifecycleState.ERRORED: [AgentLifecycleState.INIT, AgentLifecycleState.CLOSED],
        AgentLifecycleState.INTERRUPTED: [AgentLifecycleState.RUNNING, AgentLifecycleState.CLOSED],
        AgentLifecycleState.CLOSED: [],
    }

    def __init__(
        self,
        config: AgentConfig,
        client: Optional[OllamaChatClient] = None,
        skills: Optional[List[Skill]] = None,
        timeout_seconds: float = 60.0,
    ):
        self.config = config
        self.client = client or OllamaChatClient(model=config.model)
        self.skills = skills or []
        self._skill_registry = get_registry()
        self._agent = self._create_agent()

        # State machine
        self._state = AgentLifecycleState.PENDING
        self._state_lock = threading.RLock()
        self._state_history: List[Dict[str, Any]] = []

        # Timeout configuration
        self._timeout_seconds = timeout_seconds
        self._timeout_task: Optional[asyncio.Task] = None

        # Error handling
        self._error: Optional[str] = None

        # Callbacks
        self._on_state_change: Optional[Callable[[AgentLifecycleState, AgentLifecycleState], None]] = None

    def set_state_change_callback(
        self,
        callback: Callable[[AgentLifecycleState, AgentLifecycleState], None],
    ):
        """Set callback for state changes."""
        self._on_state_change = callback

    @property
    def state(self) -> AgentLifecycleState:
        """Get current state."""
        with self._state_lock:
            return self._state

    @property
    def state_value(self) -> str:
        """Get current state as string."""
        return self.state.value

    def _transition_to(self, new_state: AgentLifecycleState) -> bool:
        """
        Transition to a new state.

        Args:
            new_state: Target state

        Returns:
            True if transition was successful
        """
        with self._state_lock:
            current = self._state

            # Check if transition is valid
            if new_state not in self.VALID_TRANSITIONS.get(current, []):
                return False

            # Exit current state
            self._on_exit_state(current)

            # Update state
            self._state = new_state

            # Record history
            self._state_history.append({
                "from": current.value,
                "to": new_state.value,
                "timestamp": time.time(),
            })

            # Enter new state
            self._on_enter_state(new_state)

            # Fire callback
            if self._on_state_change:
                self._on_state_change(current, new_state)

            return True

    def _on_enter_state(self, state: AgentLifecycleState):
        """Hook called when entering a state."""
        if state == AgentLifecycleState.INIT:
            pass  # Initialization logic
        elif state == AgentLifecycleState.RUNNING:
            self._start_timeout()
        elif state == AgentLifecycleState.WAITING:
            pass  # Logic for waiting
        elif state == AgentLifecycleState.COMPLETED:
            self._cancel_timeout()
        elif state == AgentLifecycleState.ERRORED:
            self._cancel_timeout()
        elif state == AgentLifecycleState.CLOSED:
            self._cancel_timeout()

    def _on_exit_state(self, state: AgentLifecycleState):
        """Hook called when exiting a state."""
        if state == AgentLifecycleState.RUNNING:
            self._cancel_timeout()

    def _start_timeout(self):
        """Start the execution timeout."""
        self._cancel_timeout()
        try:
            loop = asyncio.get_running_loop()
            self._timeout_task = loop.create_task(self._timeout_handler())
        except RuntimeError:
            # No running event loop, skip timeout for now
            pass

    async def _timeout_handler(self):
        """Handle timeout after timeout_seconds."""
        try:
            await asyncio.sleep(self._timeout_seconds)
            if self._state == AgentLifecycleState.RUNNING:
                self._error = f"Agent timed out after {self._timeout_seconds} seconds"
                self._transition_to(AgentLifecycleState.ERRORED)
        except asyncio.CancelledError:
            pass

    def _cancel_timeout(self):
        """Cancel the timeout task."""
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None

    def interrupt(self) -> bool:
        """Interrupt the agent's execution."""
        with self._state_lock:
            if self._state in [AgentLifecycleState.RUNNING, AgentLifecycleState.WAITING]:
                self._transition_to(AgentLifecycleState.INTERRUPTED)
                return True
            return False

    def resume(self) -> bool:
        """Resume an interrupted agent."""
        with self._state_lock:
            if self._state == AgentLifecycleState.INTERRUPTED:
                self._transition_to(AgentLifecycleState.RUNNING)
                return True
            return False

    def close(self):
        """Close the agent."""
        self._transition_to(AgentLifecycleState.CLOSED)

    def get_state_history(self) -> List[Dict[str, Any]]:
        """Get state transition history."""
        with self._state_lock:
            return list(self._state_history)

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
            "state": self.state_value,
            "error": self._error,
            "state_history": len(self._state_history),
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