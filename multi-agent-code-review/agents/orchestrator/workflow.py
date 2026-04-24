"""Workflow orchestration for multi-agent system.

Supports three workflow types:
- Sequential: Step-by-step execution
- Concurrent: Parallel agent execution
- Iterative: Review -> Fix loop until passing
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class WorkflowState(Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"


class WorkflowType(Enum):
    """Type of workflow execution."""
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    ITERATIVE = "iterative"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    agent: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    status: str = "pending"


@dataclass
class WorkflowResult:
    """Result from workflow execution."""
    workflow_name: str
    state: str
    steps: List[Dict[str, Any]]
    final_result: Optional[Any] = None
    iterations: int = 0
    output: str = ""


class Workflow:
    """Base workflow class for multi-agent orchestration."""

    def __init__(
        self,
        name: str,
        workflow_type: WorkflowType = WorkflowType.SEQUENTIAL,
        description: str = "",
    ):
        self.name = name
        self.workflow_type = workflow_type
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.state = WorkflowState.PENDING
        self.agents: Dict[str, Any] = {}
        self.iteration_count = 0

    def add_step(self, name: str, agent: str, action: str, params: Dict[str, Any] = None):
        """Add a step to the workflow."""
        self.steps.append(WorkflowStep(
            name=name,
            agent=agent,
            action=action,
            params=params or {}
        ))

    def set_agents(self, agents: Dict[str, Any]):
        """Set available agents for this workflow."""
        self.agents = agents

    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """Execute the workflow."""
        self.state = WorkflowState.RUNNING

        if self.workflow_type == WorkflowType.SEQUENTIAL:
            result = await self._execute_sequential(context)
        elif self.workflow_type == WorkflowType.CONCURRENT:
            result = await self._execute_concurrent(context)
        elif self.workflow_type == WorkflowType.ITERATIVE:
            result = await self._execute_iterative(context)
        else:
            result = await self._execute_sequential(context)

        self.state = WorkflowState.COMPLETED
        return result

    async def _execute_sequential(self, context: Dict[str, Any]) -> WorkflowResult:
        """Execute steps one at a time."""
        results = []

        for step in self.steps:
            try:
                result = await self._execute_step(step, context)
                step.result = result
                step.status = "completed"
                results.append({"step": step.name, "result": result, "error": None})
            except Exception as e:
                step.error = str(e)
                step.status = "failed"
                results.append({"step": step.name, "result": None, "error": str(e)})

        return WorkflowResult(
            workflow_name=self.name,
            state=self.state.value,
            steps=results,
            final_result=results[-1] if results else None,
            iterations=1,
        )

    async def _execute_concurrent(self, context: Dict[str, Any]) -> WorkflowResult:
        """Execute independent steps in parallel."""
        tasks = []
        for step in self.steps:
            tasks.append(self._execute_step(step, context))

        step_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, (step, result) in enumerate(zip(self.steps, step_results)):
            if isinstance(result, Exception):
                step.error = str(result)
                step.status = "failed"
                results.append({"step": step.name, "result": None, "error": str(result)})
            else:
                step.result = result
                step.status = "completed"
                results.append({"step": step.name, "result": result, "error": None})

        return WorkflowResult(
            workflow_name=self.name,
            state=self.state.value,
            steps=results,
            final_result=results,
            iterations=1,
        )

    async def _execute_iterative(
        self,
        context: Dict[str, Any],
        max_iterations: int = 3,
    ) -> WorkflowResult:
        """Iterative workflow: Review -> Fix -> Review until passing."""
        results = []

        for iteration in range(max_iterations):
            self.iteration_count += 1

            for step in self.steps:
                try:
                    result = await self._execute_step(step, context)
                    step.result = result
                    step.status = "completed"
                    results.append({
                        "iteration": iteration + 1,
                        "step": step.name,
                        "result": result,
                        "error": None
                    })
                except Exception as e:
                    step.error = str(e)
                    step.status = "failed"
                    results.append({
                        "iteration": iteration + 1,
                        "step": step.name,
                        "result": None,
                        "error": str(e)
                    })

            # Check if quality threshold met
            if self._check_quality(context):
                break

        return WorkflowResult(
            workflow_name=self.name,
            state=self.state.value,
            steps=results,
            final_result=results[-1] if results else None,
            iterations=self.iteration_count,
        )

    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Any:
        """Execute a single step by routing to appropriate agent."""
        agent_name = step.agent.lower()

        if agent_name == "coordinator":
            return await self._run_coordinator(step, context)
        elif agent_name == "planner":
            return await self._run_planner(step, context)
        elif agent_name == "coder":
            return await self._run_coder(step, context)
        elif agent_name == "reviewer":
            return await self._run_reviewer(step, context)
        elif agent_name == "linter":
            return await self._run_linter(step, context)
        elif agent_name == "fixer":
            return await self._run_fixer(step, context)
        elif agent_name == "tester":
            return await self._run_tester(step, context)
        else:
            raise ValueError(f"Unknown agent: {step.agent}")

    async def _run_coordinator(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run coordinator agent."""
        from agents.coordinator import get_coordinator_agent
        agent = self.agents.get("coordinator") or get_coordinator_agent()
        prompt = step.params.get("prompt", "Coordinate the workflow")
        result = await agent.run(prompt)
        return {"response": result}

    async def _run_planner(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run planner agent."""
        from agents.planner import get_planner_agent
        agent = self.agents.get("planner") or get_planner_agent()
        prompt = step.params.get("prompt", "Create a plan")
        result = await agent.run(prompt)
        return {"plan": result}

    async def _run_coder(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run coder agent."""
        from agents.coder import get_coder_agent
        agent = self.agents.get("coder") or get_coder_agent()
        prompt = step.params.get("prompt", "Write code")
        result = await agent.run(prompt)
        return {"code": result}

    async def _run_reviewer(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run reviewer agent."""
        from agents.reviewer import get_reviewer_agent
        agent = self.agents.get("reviewer") or get_reviewer_agent()
        code = context.get("code", step.params.get("code", ""))
        result = await agent.run(f"Review this code:\n{code}")
        return {"review": result}

    async def _run_linter(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run linter agent."""
        from agents.linter import get_linter_agent
        agent = self.agents.get("linter") or get_linter_agent()
        code = context.get("code", step.params.get("code", ""))
        result = await agent.run(f"Lint this code:\n{code}")
        return {"lint": result}

    async def _run_fixer(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run fixer agent."""
        from agents.fixer import get_fixer_agent
        agent = self.agents.get("fixer") or get_fixer_agent()
        code = context.get("code", step.params.get("code", ""))
        issues = step.params.get("issues", [])
        result = await agent.run(f"Fix issues in:\n{code}\n\nIssues: {issues}")
        return {"fixed": result}

    async def _run_tester(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict:
        """Run tester agent."""
        from agents.test_agent import get_tester_agent
        agent = self.agents.get("tester") or get_tester_agent()
        code = context.get("code", step.params.get("code", ""))
        result = await agent.run(f"Generate tests for:\n{code}")
        return {"tests": result}

    def _check_quality(self, context: Dict[str, Any]) -> bool:
        """Check if quality threshold is met."""
        # Check if no critical issues
        issues = context.get("issues", [])
        critical = [i for i in issues if i.get("severity") == "critical"]
        return len(critical) == 0


class WorkflowBuilder:
    """Builder for creating workflows with fluent interface."""

    def __init__(self):
        self._workflow: Optional[Workflow] = None

    def create(
        self,
        name: str,
        workflow_type: WorkflowType = WorkflowType.SEQUENTIAL,
        description: str = "",
    ) -> "WorkflowBuilder":
        """Create a new workflow."""
        self._workflow = Workflow(name, workflow_type, description)
        return self

    def add_step(
        self,
        name: str,
        agent: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowBuilder":
        """Add a step to the workflow."""
        if self._workflow:
            self._workflow.add_step(name, agent, action, params)
        return self

    def sequential(self) -> "WorkflowBuilder":
        """Set workflow type to sequential."""
        if self._workflow:
            self._workflow.workflow_type = WorkflowType.SEQUENTIAL
        return self

    def concurrent(self) -> "WorkflowBuilder":
        """Set workflow type to concurrent."""
        if self._workflow:
            self._workflow.workflow_type = WorkflowType.CONCURRENT
        return self

    def iterative(self) -> "WorkflowBuilder":
        """Set workflow type to iterative."""
        if self._workflow:
            self._workflow.workflow_type = WorkflowType.ITERATIVE
        return self

    def build(self) -> Workflow:
        """Build and return the workflow."""
        if not self._workflow:
            raise ValueError("Workflow not created. Call create() first.")
        workflow = self._workflow
        self._workflow = None
        return workflow


class MultiAgentWorkflow:
    """High-level workflow for multi-agent development."""

    @staticmethod
    def create_development_workflow() -> Workflow:
        """Create the standard development workflow: Plan -> Code -> Review -> Fix -> Test."""
        return (WorkflowBuilder()
            .create("DevelopmentWorkflow", WorkflowType.SEQUENTIAL)
            .add_step("Planning", "planner", "create_plan")
            .add_step("Coding", "coder", "write_code")
            .add_step("Linting", "linter", "lint_code")
            .add_step("Review", "reviewer", "review_code")
            .add_step("Testing", "tester", "run_tests")
            .build())

    @staticmethod
    def create_review_workflow() -> Workflow:
        """Create the review workflow: Lint + Review in parallel, then Fix if needed."""
        return (WorkflowBuilder()
            .create("ReviewWorkflow", WorkflowType.CONCURRENT)
            .add_step("Lint", "linter", "lint_code")
            .add_step("Review", "reviewer", "review_code")
            .build())

    @staticmethod
    def create_iterative_workflow(max_iterations: int = 3) -> Workflow:
        """Create iterative workflow: Review -> Fix until passing."""
        return (WorkflowBuilder()
            .create("IterativeWorkflow", WorkflowType.ITERATIVE)
            .add_step("Review", "reviewer", "review_code")
            .add_step("Fix", "fixer", "fix_issues")
            .build())


def run_workflow(
    workflow: Workflow,
    context: Dict[str, Any],
    agents: Optional[Dict[str, Any]] = None,
) -> WorkflowResult:
    """Run a workflow synchronously."""
    if agents:
        workflow.set_agents(agents)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(workflow.execute(context))
    finally:
        loop.close()