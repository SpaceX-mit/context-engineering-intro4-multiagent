"""API for AI Coder with Collaboration Events Support."""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


class EventType(Enum):
    """Collaboration event types based on Codex."""
    AGENT_SPAWNED = "agent_spawned"
    AGENT_CLOSED = "agent_closed"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_MESSAGE = "agent_message"
    WORKFLOW_PROGRESS = "workflow_progress"
    TOOL_OUTPUT = "tool_output"
    ERROR = "error"


@dataclass
class CollaborationEvent:
    """A collaboration event between agents."""
    event_type: EventType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agent_nickname: Optional[str] = None
    agent_role: Optional[str] = None
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "agent_nickname": self.agent_nickname,
            "agent_role": self.agent_role,
            "message": self.message,
            "data": self.data,
            "model": self.model,
        }

    def to_display(self) -> str:
        """Format for display."""
        icon = {
            EventType.AGENT_SPAWNED: "✦",
            EventType.AGENT_CLOSED: "✓",
            EventType.AGENT_STATUS_CHANGED: "→",
            EventType.AGENT_MESSAGE: "💬",
            EventType.WORKFLOW_PROGRESS: "📋",
            EventType.TOOL_OUTPUT: "⚙️",
            EventType.ERROR: "❌",
        }.get(self.event_type, "•")

        agent = ""
        if self.agent_nickname:
            agent = f"**{self.agent_nickname}**"
            if self.agent_role:
                agent += f" [{self.agent_role}]"

        return f"{icon} {agent} {self.message}"


class EventEmitter:
    """Simple event emitter for collaboration events."""

    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}
        self._events: List[CollaborationEvent] = []
        self._max_events = 100
        self._lock = threading.Lock()

    def on(self, event_type: EventType, callback: Callable):
        """Register an event listener."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event: CollaborationEvent):
        """Emit an event."""
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

        # Notify listeners
        listeners = self._listeners.get(event.event_type, [])
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                pass

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._lock:
            events = self._events
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return [e.to_dict() for e in events[-limit:]]

    def clear(self):
        """Clear all events."""
        with self._lock:
            self._events.clear()


# Global event emitter
_event_emitter = EventEmitter()


def get_event_emitter() -> EventEmitter:
    """Get the global event emitter."""
    return _event_emitter


def emit_spawn(agent_nickname: str, agent_role: str, model: str = "llama3.2"):
    """Emit agent spawn event."""
    event = CollaborationEvent(
        event_type=EventType.AGENT_SPAWNED,
        agent_nickname=agent_nickname,
        agent_role=agent_role,
        message=f"Spawned agent",
        model=model,
    )
    _event_emitter.emit(event)


def emit_close(agent_nickname: str, agent_role: str, status: str = "Completed"):
    """Emit agent close event."""
    event = CollaborationEvent(
        event_type=EventType.AGENT_CLOSED,
        agent_nickname=agent_nickname,
        agent_role=agent_role,
        message=f"Closed - {status}",
    )
    _event_emitter.emit(event)


def emit_interaction(
    sender: str,
    receiver: str,
    sender_role: str = "",
    receiver_role: str = "",
):
    """Emit agent interaction event."""
    event = CollaborationEvent(
        event_type=EventType.AGENT_MESSAGE,
        agent_nickname=sender,
        agent_role=sender_role,
        message=f"Sent input to: **{receiver}**",
        data={"receiver": receiver, "receiver_role": receiver_role},
    )
    _event_emitter.emit(event)


def emit_progress(agent: str, step: str, status: str, progress: int):
    """Emit workflow progress event."""
    event = CollaborationEvent(
        event_type=EventType.WORKFLOW_PROGRESS,
        agent_nickname=agent,
        message=f"{step}: {status}",
        data={"progress": progress, "step": step, "status": status},
    )
    _event_emitter.emit(event)


def emit_error(message: str, agent: Optional[str] = None):
    """Emit error event."""
    event = CollaborationEvent(
        event_type=EventType.ERROR,
        agent_nickname=agent,
        message=message,
    )
    _event_emitter.emit(event)


# API Routes
@app.route('/api/events', methods=['GET'])
def get_events():
    """Get recent collaboration events."""
    event_type = request.args.get('type')
    limit = int(request.args.get('limit', 50))

    et = None
    if event_type:
        try:
            et = EventType(event_type)
        except ValueError:
            return jsonify({"error": "Invalid event type"}), 400

    events = _event_emitter.get_events(et, limit)
    return jsonify({"events": events})


@app.route('/api/events/clear', methods=['POST'])
def clear_events():
    """Clear all events."""
    _event_emitter.clear()
    return jsonify({"success": True})


@app.route('/api/agents/status', methods=['GET'])
def get_agents_status():
    """Get current agent statuses."""
    return jsonify({
        "agents": [
            {"name": "Coordinator", "role": "coordinator", "status": "ready"},
            {"name": "Planner", "role": "planner", "status": "ready"},
            {"name": "Coder", "role": "coder", "status": "ready"},
            {"name": "Linter", "role": "linter", "status": "ready"},
            {"name": "Reviewer", "role": "reviewer", "status": "ready"},
            {"name": "Fixer", "role": "fixer", "status": "ready"},
            {"name": "Tester", "role": "tester", "status": "ready"},
        ]
    })


# SSE endpoint for real-time events
@app.route('/api/events/stream')
def event_stream():
    """Server-Sent Events stream for real-time updates."""
    def generate():
        import time
        client_events = set()

        while True:
            events = _event_emitter.get_events(limit=10)
            for event in events:
                event_id = f"{event['timestamp']}:{event['event_type']}"
                if event_id not in client_events:
                    client_events.add(event_id)
                    yield f"data: {json.dumps(event)}\n\n"
            time.sleep(0.5)

    from flask import Response
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
