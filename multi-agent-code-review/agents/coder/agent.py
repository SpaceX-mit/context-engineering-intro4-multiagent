"""Coder Agent - Generates code implementations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.base import AgentConfig, AgentType, BaseAgent
from core.context import WorkflowContext

from .prompts import CODER_PROMPT
from .tools import generate_code, validate_code


class CoderAgent(BaseAgent):
    """
    Coder Agent - generates code implementations.

    Responsibilities:
    - Generate code from requirements/plans
    - Validate code syntax
    - Write code to files
    - Handle basic error cases
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Coder",
                role="coder",
                instructions=CODER_PROMPT,
                agent_type=AgentType.CODER,
                model="llama3.2",
            )
        super().__init__(config)
        self._last_code: Optional[str] = None

    def implement(
        self,
        requirement: str,
        plan: Optional[Any] = None,
    ) -> str:
        """
        Implement code based on requirement.

        Args:
            requirement: User requirement
            plan: Optional implementation plan

        Returns:
            Generated code
        """
        code = generate_code(requirement, plan)
        self._last_code = code

        # Validate
        validation = validate_code(code)
        if not validation["valid"]:
            raise ValueError(f"Code validation failed: {validation['issues']}")

        return code

    def get_last_code(self) -> Optional[str]:
        """Get the last generated code."""
        return self._last_code

    def format_code(self, code: str) -> str:
        """Format code for display."""
        return f"```python\n{code}\n```"

    async def run(self, prompt: str, context: Optional[WorkflowContext] = None) -> str:
        """
        Run coder with a requirement.

        Args:
            prompt: User requirement or plan
            context: Optional workflow context

        Returns:
            Generated code
        """
        # Get requirement from context if available
        if context and context.plan:
            requirement = context.plan
        elif context and context.requirement:
            requirement = context.requirement
        else:
            requirement = prompt

        code = self.implement(requirement)

        output = f"## Generated Code\n\n"
        output += self.format_code(code)
        output += "\n\n**Validation:** Passed\n"

        return output


# Factory function
def create_coder_agent() -> CoderAgent:
    """Create a coder agent."""
    return CoderAgent()


# Lazy singleton
_coder_agent: Optional[CoderAgent] = None


def get_coder_agent() -> CoderAgent:
    """Get or create the coder agent."""
    global _coder_agent
    if _coder_agent is None:
        _coder_agent = CoderAgent()
    return _coder_agent
