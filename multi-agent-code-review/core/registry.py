"""Agent Registry - Manages all active agents and maintains agent tree structure.

Based on Codex architecture from CODEX_ANALYSIS.md:
- AgentRegistry manages active agents with metadata
- Supports agent tree for hierarchical relationships
- Thread-safe with weak references to avoid circular references
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import threading
import time
import uuid


class AgentStatus(Enum):
    """Agent lifecycle states based on Codex."""
    PENDING = "pending"          # Waiting to initialize
    INIT = "init"               # Initializing
    RUNNING = "running"         # Actively executing
    WAITING = "waiting"         # Waiting for other agents
    COMPLETED = "completed"      # Finished successfully
    ERRORED = "errored"          # Encountered an error
    INTERRUPTED = "interrupted"  # Interrupted by user
    CLOSED = "closed"           # Shutdown


@dataclass
class AgentMetadata:
    """Metadata for an agent, similar to Codex's AgentMetadata."""
    agent_id: str
    nickname: Optional[str] = None
    role: Optional[str] = None
    status: AgentStatus = AgentStatus.PENDING
    parent_id: Optional[str] = None
    spawned_at: float = field(default_factory=time.time)
    last_task_message: Optional[str] = None
    model: Optional[str] = None
    reasoning_effort: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "nickname": self.nickname,
            "role": self.role,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "spawned_at": self.spawned_at,
            "last_task_message": self.last_task_message,
            "model": self.model,
        }


class AgentRegistry:
    """
    Central registry for all active agents.

    Maintains agent tree structure similar to Codex's AgentRegistry:
    - Active agents stored in thread-safe map
    - Nickname management to avoid conflicts
    - Parent-child relationships for sub-agents

    Thread-safe implementation with locks.
    """

    def __init__(self):
        self._agents: Dict[str, AgentMetadata] = {}
        self._agent_tree: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        self._used_nicknames: set = set()
        self._nickname_reset_count: int = 0
        self._lock = threading.RLock()

    def register_agent(
        self,
        agent_id: str,
        nickname: Optional[str] = None,
        role: Optional[str] = None,
        parent_id: Optional[str] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMetadata:
        """
        Register a new agent.

        Args:
            agent_id: Unique agent identifier
            nickname: Display name for the agent
            role: Agent role (coordinator, planner, coder, etc.)
            parent_id: Parent agent ID for tree structure
            model: LLM model being used
            metadata: Additional metadata

        Returns:
            AgentMetadata for the registered agent
        """
        with self._lock:
            # Generate nickname if not provided
            if nickname is None:
                nickname = self._generate_nickname(role or "agent")

            # Ensure nickname is unique
            nickname = self._ensure_unique_nickname(nickname)

            agent = AgentMetadata(
                agent_id=agent_id,
                nickname=nickname,
                role=role,
                status=AgentStatus.PENDING,
                parent_id=parent_id,
                model=model,
                metadata=metadata or {},
            )

            self._agents[agent_id] = agent
            self._used_nicknames.add(nickname)

            # Update tree structure
            if parent_id:
                if parent_id not in self._agent_tree:
                    self._agent_tree[parent_id] = []
                self._agent_tree[parent_id].append(agent_id)

            return agent

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent and all its children.

        Args:
            agent_id: Agent to unregister

        Returns:
            True if agent was found and removed
        """
        with self._lock:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]

            # Remove from used nicknames
            if agent.nickname:
                self._used_nicknames.discard(agent.nickname)

            # Remove children recursively
            if agent_id in self._agent_tree:
                for child_id in self._agent_tree[agent_id]:
                    self.unregister_agent(child_id)
                del self._agent_tree[agent_id]

            # Remove from parent's children list
            if agent.parent_id and agent.parent_id in self._agent_tree:
                self._agent_tree[agent.parent_id].remove(agent_id)

            # Remove agent
            del self._agents[agent_id]
            return True

    def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent metadata by ID."""
        with self._lock:
            return self._agents.get(agent_id)

    def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """Update agent status."""
        with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id].status = status
            return True

    def update_agent_message(self, agent_id: str, message: str) -> bool:
        """Update agent's last task message."""
        with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id].last_task_message = message
            return True

    def list_agents(
        self,
        status: Optional[AgentStatus] = None,
        role: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> List[AgentMetadata]:
        """List agents with optional filters."""
        with self._lock:
            agents = list(self._agents.values())

            if status:
                agents = [a for a in agents if a.status == status]
            if role:
                agents = [a for a in agents if a.role == role]
            if parent_id is not None:
                agents = [a for a in agents if a.parent_id == parent_id]

            return agents

    def get_agent_tree(self, root_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get agent tree structure.

        Args:
            root_id: Start from this agent (None for all root agents)

        Returns:
            Tree structure as nested dict
        """
        with self._lock:
            if root_id is None:
                # Find root agents (no parent)
                roots = [a for a in self._agents.values() if a.parent_id is None]
                return {
                    "roots": [
                        self._build_tree_node(agent_id)
                        for agent_id in [r.agent_id for r in roots]
                    ]
                }
            else:
                return self._build_tree_node(root_id)

    def _build_tree_node(self, agent_id: str) -> Dict[str, Any]:
        """Build tree node recursively."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {}

        node = {
            "agent_id": agent_id,
            "nickname": agent.nickname,
            "role": agent.role,
            "status": agent.status.value,
            "children": [],
        }

        children = self._agent_tree.get(agent_id, [])
        for child_id in children:
            node["children"].append(self._build_tree_node(child_id))

        return node

    def get_children(self, agent_id: str) -> List[AgentMetadata]:
        """Get all children of an agent."""
        with self._lock:
            child_ids = self._agent_tree.get(agent_id, [])
            return [self._agents[cid] for cid in child_ids if cid in self._agents]

    def get_parent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get parent of an agent."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent and agent.parent_id:
                return self._agents.get(agent.parent_id)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            status_counts = {}
            for agent in self._agents.values():
                status = agent.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total_agents": len(self._agents),
                "status_counts": status_counts,
                "used_nicknames": len(self._used_nicknames),
                "nickname_reset_count": self._nickname_reset_count,
            }

    def _generate_nickname(self, role: str) -> str:
        """Generate nickname based on role."""
        role_nicknames = {
            "coordinator": "Alex",
            "planner": "Sam",
            "coder": "Codey",
            "reviewer": "Robie",
            "linter": "Lint",
            "fixer": "Fix",
            "tester": "Testy",
        }
        return role_nicknames.get(role.lower(), "Agent")

    def _ensure_unique_nickname(self, nickname: str) -> str:
        """Ensure nickname is unique, append number if needed."""
        if nickname not in self._used_nicknames:
            return nickname

        counter = 1
        while f"{nickname}{counter}" in self._used_nicknames:
            counter += 1

        return f"{nickname}{counter}"

    def reset_nicknames(self):
        """Reset all nicknames for reuse."""
        with self._lock:
            self._used_nicknames.clear()
            self._nickname_reset_count += 1


# Global registry instance
_registry: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> AgentRegistry:
    """Get or create the global agent registry."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = AgentRegistry()
        return _registry


def reset_registry():
    """Reset the global registry (for testing)."""
    global _registry
    with _registry_lock:
        _registry = None