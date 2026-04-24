"""Linter Agent - Checks code style."""

from __future__ import annotations
from typing import List, Optional

from agents.base import AgentConfig, AgentType, BaseAgent
from core.context import CodeIssue, Severity, WorkflowContext


class LinterAgent(BaseAgent):
    """Linter Agent - checks code style and formatting."""

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Linter",
                role="linter",
                instructions="Check code style and formatting",
                agent_type=AgentType.LINTER,
                model="llama3.2",
            )
        super().__init__(config)

    def lint(self, code: str) -> List[CodeIssue]:
        """Lint code and return issues."""
        issues = []

        # Check for common style issues
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            # Line too long
            if len(line) > 100:
                issues.append(CodeIssue(
                    line=i,
                    severity=Severity.LOW,
                    issue_type="style",
                    message="Line too long (>{100} chars)",
                    auto_fixable=True,
                ))

            # Trailing whitespace
            if line.rstrip() != line:
                issues.append(CodeIssue(
                    line=i,
                    severity=Severity.LOW,
                    issue_type="style",
                    message="Trailing whitespace",
                    auto_fixable=True,
                ))

            # Missing space after comma
            if ', ' not in line and ',' in line and '(' in line:
                if i > 0:
                    issues.append(CodeIssue(
                        line=i,
                        severity=Severity.LOW,
                        issue_type="style",
                        message="Missing space after comma",
                        auto_fixable=True,
                    ))

        return issues

    async def run(self, prompt: str, context: Optional[WorkflowContext] = None) -> str:
        code = context.code if context and context.code else prompt
        issues = self.lint(code)
        return f"## Linting Results\n\nFound {len(issues)} issues\n"


def create_linter_agent() -> LinterAgent:
    return LinterAgent()


_linter_agent: Optional[LinterAgent] = None


def get_linter_agent() -> LinterAgent:
    global _linter_agent
    if _linter_agent is None:
        _linter_agent = LinterAgent()
    return _linter_agent
