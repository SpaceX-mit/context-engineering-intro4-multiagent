"""Fixer Agent - Auto-fixes code issues."""

from __future__ import annotations
from typing import List, Optional

from agents.base import AgentConfig, AgentType, BaseAgent
from core.context import CodeIssue, WorkflowContext


class FixerAgent(BaseAgent):
    """Fixer Agent - auto-fixes identified issues."""

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Fixer",
                role="fixer",
                instructions="Fix code issues automatically",
                agent_type=AgentType.FIXER,
                model="llama3.2",
            )
        super().__init__(config)

    def fix(self, code: str, issues: List[CodeIssue]) -> str:
        """Fix code issues."""
        fixed_code = code
        fixed_count = 0

        for issue in issues:
            if issue.auto_fixable:
                # Apply fixes based on issue type
                if issue.issue_type == "style" and "trailing whitespace" in issue.message.lower():
                    lines = fixed_code.split('\n')
                    if issue.line and issue.line <= len(lines):
                        lines[issue.line - 1] = lines[issue.line - 1].rstrip()
                        fixed_code = '\n'.join(lines)
                        fixed_count += 1

                elif issue.issue_type == "style" and "line too long" in issue.message.lower():
                    lines = fixed_code.split('\n')
                    if issue.line and issue.line <= len(lines):
                        line = lines[issue.line - 1]
                        if len(line) > 100:
                            lines[issue.line - 1] = line[:97] + "..."
                            fixed_code = '\n'.join(lines)
                            fixed_count += 1

        return fixed_code

    async def run(self, prompt: str, context: Optional[WorkflowContext] = None) -> str:
        code = context.code if context and context.code else ""
        issues = []
        if context:
            issues = context.lint_issues + context.review_issues

        if issues:
            fixed = self.fix(code, issues)
            return f"## Fixed Code\n\nApplied {len([i for i in issues if i.auto_fixable])} fixes\n"
        return "No fixes needed\n"


def create_fixer_agent() -> FixerAgent:
    return FixerAgent()


_fixer_agent: Optional[FixerAgent] = None


def get_fixer_agent() -> FixerAgent:
    global _fixer_agent
    if _fixer_agent is None:
        _fixer_agent = FixerAgent()
    return _fixer_agent
