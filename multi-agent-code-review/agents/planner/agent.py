"""Planner Agent - Creates implementation plans."""

from __future__ import annotations

from typing import Optional

from agents.base import AgentConfig, AgentType, BaseAgent
from core.context import WorkflowContext

from .prompts import PLANNER_PROMPT
from .tools import ImplementationPlan, create_plan, estimate_effort


class PlannerAgent(BaseAgent):
    """
    Planner Agent - creates detailed implementation plans.

    Responsibilities:
    - Analyze requirements
    - Create step-by-step plans
    - Estimate complexity and effort
    - Output structured plans
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Planner",
                role="planner",
                instructions=PLANNER_PROMPT,
                agent_type=AgentType.PLANNER,
                model="llama3.2",
            )
        super().__init__(config)

    def plan(self, requirement: str) -> ImplementationPlan:
        """
        Create an implementation plan.

        Args:
            requirement: User requirement

        Returns:
            Implementation plan
        """
        return create_plan(requirement)

    def get_effort(self, plan: ImplementationPlan) -> dict:
        """Get effort estimation for a plan."""
        return estimate_effort(plan)

    def format_plan(self, plan: ImplementationPlan) -> str:
        """Format plan as a readable string."""
        output = f"# Implementation Plan\n\n"
        output += f"## Overview\n{plan.overview}\n\n"
        output += f"## Steps\n"
        for step in plan.steps:
            output += f"{step.step_number}. **{step.name}**\n"
            output += f"   - {step.description}\n"
            output += f"   - Complexity: {step.complexity}/5\n"
            output += f"   - Est. Lines: {step.estimated_lines}\n"
        output += f"\n## Files\n"
        for f in plan.files:
            output += f"- {f}\n"
        output += f"\n## Effort: {plan.estimated_effort}\n"
        return output

    async def run(self, prompt: str, context: Optional[WorkflowContext] = None) -> str:
        """
        Run planner with a requirement.

        Args:
            prompt: User requirement
            context: Optional workflow context

        Returns:
            Formatted implementation plan
        """
        # Get requirement from context if available
        if context and context.requirement:
            requirement = context.requirement
        else:
            requirement = prompt

        plan = self.plan(requirement)
        return self.format_plan(plan)


# Factory function
def create_planner_agent() -> PlannerAgent:
    """Create a planner agent."""
    return PlannerAgent()


# Lazy singleton
_planner_agent: Optional[PlannerAgent] = None


def get_planner_agent() -> PlannerAgent:
    """Get or create the planner agent."""
    global _planner_agent
    if _planner_agent is None:
        _planner_agent = PlannerAgent()
    return _planner_agent
