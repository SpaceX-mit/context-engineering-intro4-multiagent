"""Context Manager for AI Coder.

Handles token counting, context compression, and prompt optimization.
Based on OpenAI Codex context engineering.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Rough token estimation
AVG_CHARS_PER_TOKEN = 4


@dataclass
class TokenCounter:
    """Track token usage across context."""

    system: int = 0
    workspace: int = 0
    history: int = 0
    reserved: int = 2000  # Reserved for model reasoning

    @property
    def total(self) -> int:
        return self.system + self.workspace + self.history + self.reserved

    @property
    def available(self) -> int:
        """Tokens available for input."""
        return 128000 - self.total  # Assuming 128k context window

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens for text."""
        return len(text) // AVG_CHARS_PER_TOKEN

    def add_system(self, text: str):
        self.system = self.estimate_tokens(text)

    def add_workspace(self, text: str):
        self.workspace = self.estimate_tokens(text)

    def add_history(self, text: str):
        self.history = self.estimate_tokens(text)

    def needs_compaction(self, threshold: float = 0.8) -> bool:
        """Check if context needs compaction."""
        return self.total > (128000 * threshold)


@dataclass
class ContextWindow:
    """Represents a context window with limits."""

    max_tokens: int = 128000
    warning_threshold: float = 0.8
    critical_threshold: float = 0.95

    def is_warning(self, tokens: int) -> bool:
        return tokens > (self.max_tokens * self.warning_threshold)

    def is_critical(self, tokens: int) -> bool:
        return tokens > (self.max_tokens * self.critical_threshold)


class ContextManager:
    """Manages context for AI Coder agents.

    Based on Codex context management with:
    - Token counting and limits
    - Context compaction
    - Prompt caching
    """

    def __init__(
        self,
        max_tokens: int = 128000,
        compaction_threshold: float = 0.8,
    ):
        self.max_tokens = max_tokens
        self.compaction_threshold = compaction_threshold
        self.counter = TokenCounter()
        self.window = ContextWindow(max_tokens=max_tokens)

        # Compaction history
        self._compaction_count = 0
        self._last_compaction_time: Optional[float] = None

    def build_system_prompt(
        self,
        agent_name: str,
        agent_role: str,
        skills: List[str],
        workspace_context: str = "",
    ) -> str:
        """Build optimized system prompt.

        Args:
            agent_name: Name of the agent
            agent_role: Role description
            skills: Available skills
            workspace_context: Current file/project context

        Returns:
            Formatted system prompt
        """
        skills_str = ", ".join(skills) if skills else "None"

        prompt = f"""You are {agent_name}, {agent_role}.

## Skills Available
{skills_str}

## Current Workspace Context
{workspace_context or "(No specific context)"}

## Guidelines
1. Be concise and practical
2. Write working code with basic error handling
3. Execute code using the appropriate skill
4. Report results clearly

## Response Format
Always include:
1. What you're doing
2. The result/output
3. Next steps (if any)
"""

        self.counter.add_system(prompt)
        return prompt

    def should_compact(self) -> bool:
        """Check if context should be compacted."""
        return self.counter.needs_compaction(self.compaction_threshold)

    def compact_history(self, messages: List[Dict]) -> List[Dict]:
        """Compact conversation history.

        Keeps:
        - System prompt (always)
        - Recent messages (last N)
        - Key decisions/artifacts

        Args:
            messages: Conversation history

        Returns:
            Compacted message list
        """
        if not messages:
            return []

        self._compaction_count += 1
        self._last_compaction_time = time.time()

        # Keep last 10 messages plus system
        system = [m for m in messages if m.get("role") == "system"]
        others = [m for m in messages if m.get("role") != "system"][-10: *]

        # Add compaction notice
        notice = {
            "role": "system",
            "content": f"[Context compacted {self._compaction_count} times. Earlier history summarized.]"
        }

        compacted = system + [notice] + others
        self.counter.history = sum(
            self.counter.estimate_tokens(m.get("content", ""))
            for m in compacted
        )

        return compacted

    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics."""
        return {
            "total_tokens": self.counter.total,
            "available_tokens": self.counter.available,
            "system_tokens": self.counter.system,
            "workspace_tokens": self.counter.workspace,
            "history_tokens": self.counter.history,
            "compaction_count": self._compaction_count,
            "last_compaction": self._last_compaction_time,
        }

    def reset(self):
        """Reset context counters."""
        self.counter = TokenCounter()
        self._compaction_count = 0
        self._last_compaction_time = None
