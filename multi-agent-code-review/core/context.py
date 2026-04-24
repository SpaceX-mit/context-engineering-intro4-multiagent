"""Context Manager for AI Coder.

Handles token counting, context compression, and prompt optimization.
Based on OpenAI Codex context engineering.

Includes:
- WorkflowContext: PRD-compliant workflow context for agent-to-agent communication
- ContextManager: Token counting and context management
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Rough token estimation
AVG_CHARS_PER_TOKEN = 4


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CodeIssue:
    """Represents a code issue found by Linter or Reviewer.

    Based on PRD.md CodeIssue data model.
    """
    line: Optional[int] = None
    severity: Severity = Severity.MEDIUM
    issue_type: str = ""
    message: str = ""
    auto_fixable: bool = False
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "severity": self.severity.value,
            "issue_type": self.issue_type,
            "message": self.message,
            "auto_fixable": self.auto_fixable,
            "suggestion": self.suggestion,
        }


@dataclass
class WorkflowContext:
    """
    Workflow context - shared between agents during workflow execution.

    Based on PRD.md Section 4.1 WorkflowContext data structure.

    This class maintains the state throughout the workflow execution,
    allowing agents to read from and write to it as they process tasks.
    """

    # Input
    requirement: str = ""                    # User requirement
    plan: Optional[str] = None              # Planner output
    code: Optional[str] = None              # Coder generated code

    # Review results
    lint_issues: List[CodeIssue] = field(default_factory=list)
    review_issues: List[CodeIssue] = field(default_factory=list)

    # Fix
    fixed_code: Optional[str] = None          # Fixer output

    # Testing
    tests: Optional[str] = None             # Generated tests

    # Status tracking
    current_step: str = "pending"
    iteration: int = 0
    errors: List[str] = field(default_factory=list)

    # Agent tracking
    active_agents: Dict[str, str] = field(default_factory=dict)  # agent_name -> status

    # Workflow metadata
    workflow_id: Optional[str] = None
    workflow_type: str = "sequential"

    def set_requirement(self, req: str):
        """Set user requirement."""
        self.requirement = req

    def set_plan(self, plan: str):
        """Set planner output."""
        self.plan = plan
        self.current_step = "planner_completed"

    def set_code(self, code: str):
        """Set coder output."""
        self.code = code
        self.current_step = "coder_completed"

    def add_lint_issues(self, issues: List[CodeIssue]):
        """Add linter issues."""
        self.lint_issues.extend(issues)
        self.current_step = "linter_completed"

    def add_review_issues(self, issues: List[CodeIssue]):
        """Add reviewer issues."""
        self.review_issues.extend(issues)
        self.current_step = "reviewer_completed"

    def set_fixed_code(self, code: str):
        """Set fixer output."""
        self.fixed_code = code
        self.current_step = "fixer_completed"

    def set_tests(self, tests: str):
        """Set tester output."""
        self.tests = tests
        self.current_step = "tester_completed"

    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)

    def update_agent_status(self, agent_name: str, status: str):
        """Update agent status."""
        self.active_agents[agent_name] = status

    def increment_iteration(self):
        """Increment iteration counter."""
        self.iteration += 1

    def get_critical_issues(self) -> List[CodeIssue]:
        """Get critical severity issues."""
        return [i for i in self.review_issues + self.lint_issues if i.severity == Severity.CRITICAL]

    def get_auto_fixable_issues(self) -> List[CodeIssue]:
        """Get issues that can be auto-fixed."""
        return [i for i in self.lint_issues if i.auto_fixable]

    def is_quality_acceptable(self) -> bool:
        """Check if code quality is acceptable (no critical issues)."""
        return len(self.get_critical_issues()) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requirement": self.requirement,
            "plan": self.plan,
            "code": self.code[:200] + "..." if self.code and len(self.code) > 200 else self.code,
            "lint_issues_count": len(self.lint_issues),
            "review_issues_count": len(self.review_issues),
            "fixed_code": self.fixed_code[:200] + "..." if self.fixed_code and len(self.fixed_code) > 200 else self.fixed_code,
            "tests": self.tests[:200] + "..." if self.tests and len(self.tests) > 200 else self.tests,
            "current_step": self.current_step,
            "iteration": self.iteration,
            "errors": self.errors,
            "active_agents": self.active_agents,
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
        }

    def reset(self):
        """Reset context for new workflow."""
        self.requirement = ""
        self.plan = None
        self.code = None
        self.lint_issues = []
        self.review_issues = []
        self.fixed_code = None
        self.tests = None
        self.current_step = "pending"
        self.iteration = 0
        self.errors = []
        self.active_agents = {}


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
        others = [m for m in messages if m.get("role") != "system"][-10:]

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
