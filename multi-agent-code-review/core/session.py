"""Session Manager for AI Coder.

Thread-based conversation management.
Based on OpenAI Codex session/thread model.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import rich

# Message types
class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    """Single message in a session."""
    id: str
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> Message:
        return cls(
            id=data["id"],
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Artifact:
    """Code/result artifact from a session."""
    id: str
    name: str
    type: str  # "file", "code", "result"
    content: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "content": self.content,
            "created_at": self.created_at,
        }


class SessionStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPACTED = "compacted"


class Session:
    """Represents a conversation session/thread.

    Based on Codex thread model with:
    - Multi-turn conversations
    - State persistence
    - Fork/branch support
    - Context compaction
    """

    def __init__(
        self,
        id: Optional[str] = None,
        model: str = "llama3.2",
        workspace_path: str = ".",
        parent_id: Optional[str] = None,
    ):
        self.id = id or f"session_{uuid.uuid4().hex[:12]}"
        self.model = model
        self.workspace_path = workspace_path
        self.parent_id = parent_id

        self.messages: List[Message] = []
        self.artifacts: List[Artifact] = []
        self.status = SessionStatus.ACTIVE

        self.created_at = time.time()
        self.updated_at = time.time()
        self.last_active_at = time.time()

        # Metadata
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.tags: List[str] = []

        # Context stats
        self.compaction_count = 0
        self.total_tokens = 0

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> Message:
        """Add a message to the session."""
        msg = Message(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        self.last_active_at = time.time()
        self.updated_at = time.time()
        return msg

    def add_user_message(self, content: str) -> Message:
        """Add a user message."""
        return self.add_message(MessageRole.USER.value, content)

    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None) -> Message:
        """Add an assistant message."""
        return self.add_message(MessageRole.ASSISTANT.value, content, metadata)

    def add_system_message(self, content: str) -> Message:
        """Add a system message."""
        return self.add_message(MessageRole.SYSTEM.value, content)

    def add_artifact(self, name: str, type: str, content: str) -> Artifact:
        """Add an artifact (code file, result, etc)."""
        artifact = Artifact(
            id=f"art_{uuid.uuid4().hex[:12]}",
            name=name,
            type=type,
            content=content,
        )
        self.artifacts.append(artifact)
        return artifact

    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation history as dicts."""
        msgs = self.messages if limit is None else self.messages[-limit:]
        return [m.to_dict() for m in msgs]

    def get_context_window(self, max_messages: int = 20) -> str:
        """Get recent context as string."""
        recent = self.messages[-max_messages:] if self.messages else []
        lines = []
        for msg in recent:
            role = msg.role.upper()
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def compact(self) -> int:
        """Compact the session, keeping recent messages.

        Returns:
            Number of messages removed
        """
        if len(self.messages) <= 10:
            return 0

        # Keep system messages and last N others
        system_msgs = [m for m in self.messages if m.role == MessageRole.SYSTEM.value]
        other_msgs = [m for m in self.messages if m.role != MessageRole.SYSTEM.value]

        # Keep last 10 non-system messages
        keep_msgs = other_msgs[-10:]

        # Add summary
        summary = Message(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            role=MessageRole.SYSTEM.value,
            content=f"[Earlier conversation summarized. {len(other_msgs) - 10} messages compacted.]",
        )

        self.messages = system_msgs + [summary] + keep_msgs
        self.compaction_count += 1
        self.status = SessionStatus.ACTIVE

        return len(other_msgs) - 10

    def fork(self) -> Session:
        """Create a forked copy of this session."""
        new_session = Session(
            model=self.model,
            workspace_path=self.workspace_path,
            parent_id=self.id,
        )
        new_session.messages = self.messages.copy()
        new_session.artifacts = self.artifacts.copy()
        new_session.name = f"{self.name or 'Session'} (fork)"
        return new_session

    def archive(self):
        """Archive the session."""
        self.status = SessionStatus.ARCHIVED

    def to_dict(self) -> Dict:
        """Serialize session to dict."""
        return {
            "id": self.id,
            "model": self.model,
            "workspace_path": self.workspace_path,
            "parent_id": self.parent_id,
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_active_at": self.last_active_at,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "compaction_count": self.compaction_count,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> Session:
        """Deserialize session from dict."""
        session = cls(
            id=data["id"],
            model=data.get("model", "llama3.2"),
            workspace_path=data.get("workspace_path", "."),
            parent_id=data.get("parent_id"),
        )
        session.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        session.artifacts = [Artifact(**a) for a in data.get("artifacts", [])]
        session.status = SessionStatus(data.get("status", "active"))
        session.created_at = data.get("created_at", time.time())
        session.updated_at = data.get("updated_at", time.time())
        session.last_active_at = data.get("last_active_at", time.time())
        session.name = data.get("name")
        session.description = data.get("description")
        session.tags = data.get("tags", [])
        session.compaction_count = data.get("compaction_count", 0)
        return session


class SessionManager:
    """Manager for multiple sessions.

    Handles session creation, persistence, and retrieval.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or "./sessions"
        self._sessions: Dict[str, Session] = {}
        self._active_session_id: Optional[str] = None

        if self.storage_path:
            os.makedirs(self.storage_path, exist_ok=True)

    def create_session(
        self,
        model: str = "llama3.2",
        workspace_path: str = ".",
        **kwargs,
    ) -> Session:
        """Create a new session."""
        session = Session(
            model=model,
            workspace_path=workspace_path,
            **kwargs,
        )
        self._sessions[session.id] = session
        self._active_session_id = session.id
        self._persist_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load from disk
        session = self._load_session(session_id)
        if session:
            self._sessions[session_id] = session
        return session

    def get_active_session(self) -> Optional[Session]:
        """Get the active session."""
        if self._active_session_id:
            return self.get_session(self._active_session_id)
        return None

    def set_active_session(self, session_id: str):
        """Set the active session."""
        if session_id in self._sessions or self.get_session(session_id):
            self._active_session_id = session_id

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 20,
    ) -> List[Session]:
        """List all sessions."""
        sessions = list(self._sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        # Sort by last_active_at descending
        sessions.sort(key=lambda s: s.last_active_at, reverse=True)

        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

        # Remove from disk
        if self.storage_path:
            path = Path(self.storage_path) / f"{session_id}.json"
            if path.exists():
                path.unlink()

        if self._active_session_id == session_id:
            self._active_session_id = None

        return True

    def _persist_session(self, session: Session):
        """Save session to disk."""
        if not self.storage_path:
            return

        path = Path(self.storage_path) / f"{session.id}.json"
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def _load_session(self, session_id: str) -> Optional[Session]:
        """Load session from disk."""
        if not self.storage_path:
            return None

        path = Path(self.storage_path) / f"{session_id}.json"
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return Session.from_dict(data)
        except Exception:
            return None
