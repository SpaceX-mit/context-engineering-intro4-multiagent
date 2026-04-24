"""Coordinator Agent - Orchestrates multi-agent workflows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.base import AgentConfig, AgentResult, AgentType, BaseAgent
from core.context import WorkflowContext
from core.orchestrator import WorkflowOrchestrator, get_orchestrator

from .prompts import COORDINATOR_PROMPT
from .tools import (
    RequirementAnalysis,
    aggregate_results,
    decompose_tasks,
    parse_requirement,
)


class CoordinatorAgent(BaseAgent):
    """
    Coordinator Agent - orchestrates the entire development workflow.

    Responsibilities:
    - Parse and analyze user requirements
    - Select appropriate workflow
    - Delegate tasks to specialized agents
    - Aggregate results and report progress
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        orchestrator: Optional[WorkflowOrchestrator] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="Coordinator",
                role="coordinator",
                instructions=COORDINATOR_PROMPT,
                agent_type=AgentType.COORDINATOR,
                model="llama3.2",
            )

        super().__init__(config)
        self._orchestrator = orchestrator or get_orchestrator()
        self._current_analysis: Optional[RequirementAnalysis] = None
        self._execution_results: List[Dict[str, Any]] = []

    def analyze_requirement(self, requirement: str) -> RequirementAnalysis:
        """
        Analyze a user requirement.

        Args:
            requirement: Raw user requirement

        Returns:
            Structured requirement analysis
        """
        self._current_analysis = parse_requirement(requirement)
        return self._current_analysis

    def decompose_tasks(self, analysis: RequirementAnalysis) -> List[Any]:
        """
        Decompose analysis into executable tasks.

        Args:
            analysis: Requirement analysis

        Returns:
            List of tasks
        """
        return decompose_tasks(analysis)

    def select_workflow(self, analysis: RequirementAnalysis) -> str:
        """
        Select appropriate workflow for the requirement.

        Args:
            analysis: Requirement analysis

        Returns:
            Workflow ID
        """
        workflow_map = {
            "sequential": "developm-1",  # DevelopmentWorkflow
            "concurrent": "review-1",    # ReviewWorkflow
            "iterative": "iterat-1",      # IterativeWorkflow
        }
        return workflow_map.get(analysis.workflow_type, "developm-1")

    async def execute_workflow(
        self,
        workflow_id: str,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute a workflow and track results.

        Args:
            workflow_id: Workflow to execute
            context: Workflow context

        Returns:
            Execution result summary
        """
        result = await self._orchestrator.execute_workflow(workflow_id, context)
        self._execution_results.append({
            "workflow_id": workflow_id,
            "status": result.status.value,
            "steps_completed": result.steps_completed,
            "errors": result.errors,
        })
        return {
            "status": result.status.value,
            "steps_completed": result.steps_completed,
            "total_steps": result.total_steps,
            "errors": result.errors,
        }

    def aggregate_results(self) -> Dict[str, Any]:
        """
        Aggregate all execution results.

        Returns:
            Aggregated result summary
        """
        return aggregate_results(self._execution_results)

    def get_progress(self) -> Dict[str, Any]:
        """Get current execution progress."""
        return {
            "analysis": self._current_analysis.summary if self._current_analysis else None,
            "tasks_completed": len(self._execution_results),
            "results": self._execution_results,
        }

    async def run(self, prompt: str, context: Optional[WorkflowContext] = None) -> str:
        """
        Run coordinator with a requirement prompt.

        Args:
            prompt: User requirement
            context: Optional workflow context

        Returns:
            Coordinator response with task breakdown
        """
        # Analyze requirement
        analysis = self.analyze_requirement(prompt)

        # Generate task breakdown
        tasks = self.decompose_tasks(analysis)

        # Build response
        response = f"""## Requirement Analysis

**Summary:** {analysis.summary}
**Complexity:** {analysis.complexity}/5
**Workflow:** {analysis.workflow_type}
**Agents:** {' -> '.join(analysis.agent_sequence)}

## Task Breakdown

"""
        for i, task in enumerate(tasks, 1):
            response += f"{i}. **{task.name}** ({task.agent})\n"

        response += "\n## Delegation Plan\n"
        response += "Ready to delegate tasks to specialized agents.\n"

        return response


# Factory function
def create_coordinator_agent() -> CoordinatorAgent:
    """Create a coordinator agent."""
    return CoordinatorAgent()


# Lazy singleton
_coordinator_agent: Optional[CoordinatorAgent] = None


def get_coordinator_agent() -> CoordinatorAgent:
    """Get or create the coordinator agent."""
    global _coordinator_agent
    if _coordinator_agent is None:
        _coordinator_agent = CoordinatorAgent()
    return _coordinator_agent
