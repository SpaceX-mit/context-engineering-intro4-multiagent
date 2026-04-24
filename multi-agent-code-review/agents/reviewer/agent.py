"""Reviewer Agent - Reviews code quality."""

from __future__ import annotations

from typing import List, Optional

from agents.base import AgentConfig, AgentType, BaseAgent
from core.context import CodeIssue, WorkflowContext

from .prompts import REVIEWER_PROMPT
from .tools import (
    ReviewResult,
    check_security,
    format_review_report,
    review_code,
)


class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent - reviews code quality and security.

    Responsibilities:
    - Review code for quality issues
    - Check for security vulnerabilities
    - Verify logic correctness
    - Provide actionable feedback
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Reviewer",
                role="reviewer",
                instructions=REVIEWER_PROMPT,
                agent_type=AgentType.REVIEWER,
                model="llama3.2",
            )
        super().__init__(config)
        self._last_review: Optional[ReviewResult] = None

    def review(self, code: str) -> ReviewResult:
        """
        Review code.

        Args:
            code: Python code to review

        Returns:
            Review result
        """
        result = review_code(code)
        self._last_review = result
        return result

    def check_security(self, code: str) -> List[CodeIssue]:
        """Check for security issues."""
        return check_security(code)

    def get_last_review(self) -> Optional[ReviewResult]:
        """Get the last review result."""
        return self._last_review

    def get_critical_issues(self) -> List[CodeIssue]:
        """Get critical issues from last review."""
        if self._last_review:
            return [i for i in self._last_review.issues if i.severity.value == "critical"]
        return []

    async def run(self, prompt: str, context: Optional[WorkflowContext] = None) -> str:
        """
        Run reviewer on code.

        Args:
            prompt: Code or context
            context: Optional workflow context

        Returns:
            Review report
        """
        # Get code from context if available
        if context and context.code:
            code = context.code
        else:
            code = prompt

        result = self.review(code)

        output = format_review_report(result)
        output += f"\n**Overall:** {'Pass' if result.score >= 70 else 'Needs Improvement'}\n"

        return output


# Factory function
def create_reviewer_agent() -> ReviewerAgent:
    """Create a reviewer agent."""
    return ReviewerAgent()


# Lazy singleton
_reviewer_agent: Optional[ReviewerAgent] = None


def get_reviewer_agent() -> ReviewerAgent:
    """Get or create the reviewer agent."""
    global _reviewer_agent
    if _reviewer_agent is None:
        _reviewer_agent = ReviewerAgent()
    return _reviewer_agent
