"""Workflow orchestration for multi-agent system."""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio


class WorkflowState(Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    agent: str
    action: str
    params: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None


class Workflow:
    """Base workflow class for multi-agent orchestration."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.state = WorkflowState.PENDING

    def add_step(self, name: str, agent: str, action: str, params: Dict[str, Any] = None):
        """Add a step to the workflow."""
        self.steps.append(WorkflowStep(
            name=name,
            agent=agent,
            action=action,
            params=params or {}
        ))

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow."""
        self.state = WorkflowState.RUNNING
        results = []

        for step in self.steps:
            try:
                result = await self._execute_step(step, context)
                step.result = result
                results.append({"step": step.name, "result": result, "error": None})
            except Exception as e:
                step.error = str(e)
                results.append({"step": step.name, "result": None, "error": str(e)})

        self.state = WorkflowState.COMPLETED
        return {
            "workflow": self.name,
            "state": self.state.value,
            "steps": results,
            "final_result": results[-1] if results else None
        }

    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Any:
        """Execute a single step."""
        # Route to appropriate agent
        if step.agent == "linter":
            return await self._run_linter(step, context)
        elif step.agent == "reviewer":
            return await self._run_reviewer(step, context)
        elif step.agent == "fixer":
            return await self._run_fixer(step, context)
        elif step.agent == "coder":
            return await self._run_coder(step, context)
        else:
            raise ValueError(f"Unknown agent: {step.agent}")

    async def _run_linter(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run linter agent."""
        from tools.linter import lint_code
        code = context.get("code", "")
        return {"lint_result": lint_code(code, "python")}

    async def _run_reviewer(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run reviewer agent."""
        from tools.code_analysis import analyze_code_structure
        code = context.get("code", "")
        return {"analysis": analyze_code_structure(code, "python")}

    async def _run_fixer(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run fixer agent."""
        from agents.coder import get_coder
        agent = get_coder()
        prompt = step.params.get("prompt", "Fix this code")
        result = await agent.run(prompt)
        return {"fixed_code": result.output if hasattr(result, 'output') else str(result)}

    async def _run_coder(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run coder agent."""
        from agents.coder import get_coder
        agent = get_coder()
        prompt = step.params.get("prompt", "Generate code")
        result = await agent.run(prompt)
        return {"code": result.output if hasattr(result, 'output') else str(result)}


class WorkflowBuilder:
    """Builder for creating workflows."""

    def __init__(self):
        self.workflow = None

    def create(self, name: str, description: str = "") -> "WorkflowBuilder":
        """Create a new workflow."""
        self.workflow = Workflow(name, description)
        return self

    def add_lint_step(self, name: str = "Lint") -> "WorkflowBuilder":
        """Add a lint step."""
        self.workflow.add_step(name, "linter", "lint")
        return self

    def add_review_step(self, name: str = "Review") -> "WorkflowBuilder":
        """Add a review step."""
        self.workflow.add_step(name, "reviewer", "review")
        return self

    def add_fix_step(self, name: str = "Fix", prompt: str = "") -> "WorkflowBuilder":
        """Add a fix step."""
        self.workflow.add_step(name, "fixer", "fix", {"prompt": prompt})
        return self

    def add_coder_step(self, name: str = "Generate", prompt: str = "") -> "WorkflowBuilder":
        """Add a coder step."""
        self.workflow.add_step(name, "coder", "generate", {"prompt": prompt})
        return self

    def build(self) -> Workflow:
        """Build and return the workflow."""
        return self.workflow