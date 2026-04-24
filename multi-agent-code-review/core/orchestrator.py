"""Workflow Orchestrator - Manages workflow execution across agents.

Based on PRD.md Section 5 and Codex architecture:
- register_workflow: Register a workflow definition
- execute_workflow: Execute a workflow with context
- pause/resume/cancel: Workflow lifecycle management
- Sequential/Concurrent/Iterative execution modes
- DATA FLOW: Each agent's input comes from the previous agent's output
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.context import WorkflowContext
from core.registry import get_registry, AgentStatus


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Individual step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class StepInput:
    """Input data for a workflow step.

    Contains data from:
    - Previous step's output (via output_to field)
    - Initial requirement (for first step)
    - Combined data from multiple previous steps
    """
    step_name: str
    agent: str
    data: Any  # The actual input data for this step
    source: str  # Where this data came from (e.g., "requirement", "planner.output")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_text(self) -> str:
        """Get input as text."""
        if isinstance(self.data, str):
            return self.data
        return str(self.data)

    def get_dict(self) -> Dict[str, Any]:
        """Get input as dict."""
        if isinstance(self.data, dict):
            return self.data
        return {"data": self.data}


@dataclass
class StepOutput:
    """Output data from a workflow step."""
    step_name: str
    agent: str
    result: Any
    output_key: str  # The key this output is stored under
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    agent: str
    action: str
    input_from: List[str] = field(default_factory=list)  # Sources for input data
    output_to: Optional[str] = None  # Where to store the output
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    input_data: Optional[StepInput] = None  # Computed input for this step
    output_data: Optional[StepOutput] = None  # Output from this step
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class WorkflowDefinition:
    """Workflow definition with steps and configuration."""
    id: str
    name: str
    workflow_type: str  # "sequential", "concurrent", "iterative"
    steps: List[WorkflowStep] = field(default_factory=list)
    max_iterations: int = 1
    exit_condition: Optional[str] = None  # e.g., "no_critical_issues"

    @classmethod
    def create(
        cls,
        name: str,
        steps: List[Dict[str, Any]],
        workflow_type: str = "sequential",
        max_iterations: int = 1,
        exit_condition: Optional[str] = None,
    ) -> "WorkflowDefinition":
        """Create workflow definition from dict config."""
        workflow_steps = [
            WorkflowStep(
                name=s.get("name", s["agent"]),
                agent=s["agent"],
                action=s.get("action", "run"),
                input_from=s.get("input", []) if isinstance(s.get("input"), list) else [s.get("input", "")],
                output_to=s.get("output"),
            )
            for s in steps
        ]
        return cls(
            id=str(uuid.uuid4())[:8],
            name=name,
            workflow_type=workflow_type,
            steps=workflow_steps,
            max_iterations=max_iterations,
            exit_condition=exit_condition,
        )


@dataclass
class WorkflowExecution:
    """Runtime state of a workflow execution."""
    definition: WorkflowDefinition
    context: WorkflowContext
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_index: int = 0
    current_iteration: int = 1
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    step_outputs: Dict[str, StepOutput] = field(default_factory=dict)  # Key: output key (e.g., "plan", "code")
    errors: List[str] = field(default_factory=list)

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current step being executed."""
        if self.current_step_index < len(self.definition.steps):
            return self.definition.steps[self.current_step_index]
        return None

    def get_input_for_step(self, step: WorkflowStep) -> StepInput:
        """Build the input for a step from previous outputs.

        Data flow:
        - For "requirement" input: use context.requirement
        - For "plan" input: use previous planner output
        - For "code" input: use previous coder output
        - For "issues": combine lint + review outputs
        """
        if step.input_from:
            # Collect data from all sources
            all_data = {}
            sources = []

            for source_key in step.input_from:
                if source_key == "requirement":
                    all_data["requirement"] = self.context.requirement
                    sources.append("context.requirement")
                elif source_key == "plan":
                    if "plan" in self.step_outputs:
                        all_data["plan"] = self.step_outputs["plan"].result
                        sources.append("planner.output")
                elif source_key == "code":
                    if "code" in self.step_outputs:
                        all_data["code"] = self.step_outputs["code"].result
                        sources.append("coder.output")
                    elif self.context.code:
                        all_data["code"] = self.context.code
                        sources.append("context.code")
                elif source_key == "lint_issues":
                    if "lint_issues" in self.step_outputs:
                        all_data["lint_issues"] = self.step_outputs["lint_issues"].result
                        sources.append("linter.output")
                elif source_key == "review_issues":
                    if "review_issues" in self.step_outputs:
                        all_data["review_issues"] = self.step_outputs["review_issues"].result
                        sources.append("reviewer.output")
                elif source_key == "issues":
                    # Combine all issues
                    issues = []
                    if "lint_issues" in self.step_outputs:
                        issues.extend(self.step_outputs["lint_issues"].result or [])
                    if "review_issues" in self.step_outputs:
                        issues.extend(self.step_outputs["review_issues"].result or [])
                    all_data["issues"] = issues
                    sources.append("combined_issues")
                elif source_key == "fixed_code":
                    if "fixed_code" in self.step_outputs:
                        all_data["fixed_code"] = self.step_outputs["fixed_code"].result
                        sources.append("fixer.output")
                elif source_key == "tests":
                    if "tests" in self.step_outputs:
                        all_data["tests"] = self.step_outputs["tests"].result
                        sources.append("tester.output")
                elif source_key in self.step_outputs:
                    all_data[source_key] = self.step_outputs[source_key].result
                    sources.append(f"{source_key}.output")

            # Return the data - if single source, return that directly
            if len(step.input_from) == 1:
                source = step.input_from[0]
                data = all_data.get(source, all_data.get(list(all_data.keys())[0] if all_data else None))
            else:
                data = all_data

            return StepInput(
                step_name=step.name,
                agent=step.agent,
                data=data,
                source=" -> ".join(sources) if sources else "unknown",
            )

        # No input specified, return None
        return StepInput(
            step_name=step.name,
            agent=step.agent,
            data=None,
            source="none",
        )


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    status: WorkflowStatus
    context: WorkflowContext
    steps_completed: int
    total_steps: int
    iterations: int
    errors: List[str] = field(default_factory=list)
    duration_seconds: Optional[float] = None


class WorkflowOrchestrator:
    """
    Orchestrates multi-agent workflows.

    Features:
    - Register and execute workflows
    - Support sequential, concurrent, iterative execution
    - Pause, resume, cancel workflows
    - Real-time status tracking
    - Context propagation between agents
    """

    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._step_handlers: Dict[str, Callable] = {}
        self._lock = threading.RLock()

        # Pre-defined workflows from PRD.md
        self._register_builtin_workflows()

    def _register_builtin_workflows(self):
        """Register workflows defined in PRD.md Section 5."""
        # Development Workflow
        self.register_workflow(WorkflowDefinition.create(
            name="DevelopmentWorkflow",
            workflow_type="sequential",
            steps=[
                {"agent": "coordinator", "action": "analyze", "name": "analyze"},
                {"agent": "planner", "action": "plan", "input": "requirement", "output": "plan", "name": "plan"},
                {"agent": "coder", "action": "implement", "input": "plan", "output": "code", "name": "implement"},
                {"agent": "linter", "action": "lint", "input": "code", "output": "lint_issues", "name": "lint"},
                {"agent": "reviewer", "action": "review", "input": "code", "output": "review_issues", "name": "review"},
                {"agent": "fixer", "action": "fix", "input": ["code", "issues"], "output": "fixed_code", "name": "fix"},
                {"agent": "tester", "action": "test", "input": "fixed_code", "output": "tests", "name": "test"},
            ],
        ))

        # Review Workflow
        self.register_workflow(WorkflowDefinition.create(
            name="ReviewWorkflow",
            workflow_type="concurrent",
            steps=[
                {"agent": "linter", "action": "lint", "input": "code", "name": "lint"},
                {"agent": "reviewer", "action": "review", "input": "code", "name": "review"},
            ],
        ))

        # Iterative Workflow
        self.register_workflow(WorkflowDefinition.create(
            name="IterativeWorkflow",
            workflow_type="iterative",
            max_iterations=3,
            exit_condition="no_critical_issues",
            steps=[
                {"agent": "reviewer", "action": "review", "name": "review"},
                {"agent": "fixer", "action": "fix", "name": "fix"},
            ],
        ))

    def register_workflow(self, workflow: WorkflowDefinition) -> str:
        """
        Register a workflow definition.

        Args:
            workflow: Workflow definition to register

        Returns:
            Workflow ID
        """
        with self._lock:
            self._workflows[workflow.id] = workflow
            return workflow.id

    def register_step_handler(
        self,
        agent: str,
        action: str,
        handler: Callable[[WorkflowContext, WorkflowStep], Any],
    ):
        """Register a handler for an agent action."""
        key = f"{agent}:{action}"
        self._step_handlers[key] = handler

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID."""
        with self._lock:
            return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[WorkflowDefinition]:
        """List all registered workflows."""
        with self._lock:
            return list(self._workflows.values())

    async def execute_workflow(
        self,
        workflow_id: str,
        context: WorkflowContext,
    ) -> WorkflowResult:
        """
        Execute a workflow.

        Args:
            workflow_id: ID of the workflow to execute
            context: Workflow context with input data

        Returns:
            Workflow result with execution details
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                context=context,
                steps_completed=0,
                total_steps=len(workflow.steps),
                iterations=0,
                errors=[f"Workflow {workflow_id} not found"],
            )

        # Create execution
        execution = WorkflowExecution(
            definition=workflow,
            context=context,
            status=WorkflowStatus.RUNNING,
            started_at=time.time(),
        )
        with self._lock:
            self._executions[workflow_id] = execution

        try:
            # Execute based on workflow type
            if workflow.workflow_type == "sequential":
                await self._execute_sequential(execution)
            elif workflow.workflow_type == "concurrent":
                await self._execute_concurrent(execution)
            elif workflow.workflow_type == "iterative":
                await self._execute_iterative(execution)
            else:
                raise ValueError(f"Unknown workflow type: {workflow.workflow_type}")

            # Check exit condition for iterative
            if workflow.exit_condition == "no_critical_issues":
                if context.get_critical_issues():
                    execution.status = WorkflowStatus.FAILED
                    execution.errors.append("Exit condition not met: critical issues remain")
                else:
                    execution.status = WorkflowStatus.COMPLETED

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.errors.append(str(e))

        execution.completed_at = time.time()
        return self._create_result(execution)

    async def _execute_sequential(self, execution: WorkflowExecution):
        """Execute steps sequentially."""
        for i, step in enumerate(execution.definition.steps):
            execution.current_step_index = i
            step.status = StepStatus.RUNNING
            step.started_at = time.time()

            try:
                result = await self._execute_step(execution, step)
                step.result = result
                step.status = StepStatus.COMPLETED
                execution.context.current_step = f"{step.agent}_completed"
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                execution.errors.append(f"Step {step.name} failed: {e}")
                raise

            step.completed_at = time.time()

        execution.status = WorkflowStatus.COMPLETED

    async def _execute_concurrent(self, execution: WorkflowExecution):
        """Execute independent steps concurrently."""
        tasks = []
        for i, step in enumerate(execution.definition.steps):
            execution.current_step_index = i
            step.status = StepStatus.RUNNING
            step.started_at = time.time()
            tasks.append(self._execute_step_with_tracking(execution, step, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures
        for i, result in enumerate(results):
            step = execution.definition.steps[i]
            if isinstance(result, Exception):
                step.status = StepStatus.FAILED
                step.error = str(result)
                execution.errors.append(f"Step {step.name} failed: {result}")
            else:
                step.result = result
                step.status = StepStatus.COMPLETED
                step.completed_at = time.time()

        if execution.errors:
            execution.status = WorkflowStatus.FAILED
        else:
            execution.status = WorkflowStatus.COMPLETED

    async def _execute_iterative(self, execution: WorkflowExecution):
        """Execute steps iteratively until exit condition is met."""
        max_iterations = execution.definition.max_iterations

        for iteration in range(max_iterations):
            execution.current_iteration = iteration + 1
            execution.context.increment_iteration()

            # Run review and fix steps
            for i, step in enumerate(execution.definition.steps):
                execution.current_step_index = i
                step.status = StepStatus.RUNNING
                step.started_at = time.time()

                try:
                    result = await self._execute_step(execution, step)
                    step.result = result
                    step.status = StepStatus.COMPLETED
                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    execution.errors.append(f"Iteration {iteration + 1}, Step {step.name} failed: {e}")
                    raise

                step.completed_at = time.time()

            # Check exit condition
            if execution.context.get_critical_issues():
                continue  # Continue to next iteration
            else:
                break  # Exit condition met

        execution.status = WorkflowStatus.COMPLETED

    async def _execute_step(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep,
    ) -> Any:
        """
        Execute a single step with proper data flow.

        Data flow:
        1. Build input from previous step outputs (via input_from field)
        2. Pass input to handler
        3. Store output under the output_to key
        """
        # Build input for this step
        step_input = execution.get_input_for_step(step)
        step.input_data = step_input

        # Call the handler with input
        handler_key = f"{step.agent}:{step.action}"
        handler = self._step_handlers.get(handler_key)

        if handler:
            # Handler receives: step_input (the computed input)
            result = await handler(step_input, execution.context)
        else:
            # Simulate step execution if no handler
            await asyncio.sleep(0.1)
            result = {"status": "completed", "agent": step.agent, "action": step.action}

        # Store output under the output_to key
        output_key = step.output_to or step.name
        step_output = StepOutput(
            step_name=step.name,
            agent=step.agent,
            result=result,
            output_key=output_key,
            success=True,
        )
        step.output_data = step_output
        execution.step_outputs[output_key] = step_output

        # Also update context based on output
        self._update_context_from_output(execution.context, step, result)

        return result

    def _update_context_from_output(
        self,
        context: WorkflowContext,
        step: WorkflowStep,
        result: Any,
    ):
        """Update context based on step output."""
        output_key = step.output_to or step.name

        # Map output keys to context fields
        context_updates = {
            "plan": lambda r: context.set_plan(r if isinstance(r, str) else str(r)),
            "code": lambda r: context.set_code(r if isinstance(r, str) else str(r)),
            "lint_issues": lambda r: context.add_lint_issues(r if isinstance(r, list) else []),
            "review_issues": lambda r: context.add_review_issues(r if isinstance(r, list) else []),
            "fixed_code": lambda r: context.set_fixed_code(r if isinstance(r, str) else str(r)),
            "tests": lambda r: context.set_tests(r if isinstance(r, str) else str(r)),
        }

        if output_key in context_updates:
            try:
                context_updates[output_key](result)
            except Exception:
                pass  # Ignore update errors

    async def _execute_step_with_tracking(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep,
        index: int,
    ) -> Any:
        """Execute step and track results."""
        try:
            result = await self._execute_step(execution, step)
            return result
        except Exception as e:
            # Store error in step output
            step.output_data = StepOutput(
                step_name=step.name,
                agent=step.agent,
                result=None,
                output_key=step.output_to or step.name,
                success=False,
                error=str(e),
            )
            raise

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow."""
        with self._lock:
            if workflow_id not in self._executions:
                return False
            exec = self._executions[workflow_id]
            if exec.status == WorkflowStatus.RUNNING:
                exec.status = WorkflowStatus.PAUSED
                return True
            return False

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        with self._lock:
            if workflow_id not in self._executions:
                return False
            exec = self._executions[workflow_id]
            if exec.status == WorkflowStatus.PAUSED:
                exec.status = WorkflowStatus.RUNNING
                return True
            return False

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow execution."""
        with self._lock:
            if workflow_id not in self._executions:
                return False
            exec = self._executions[workflow_id]
            exec.status = WorkflowStatus.CANCELLED
            exec.completed_at = time.time()
            return True

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow execution."""
        with self._lock:
            if workflow_id not in self._executions:
                return None

            exec = self._executions[workflow_id]
            return {
                "workflow_id": workflow_id,
                "name": exec.definition.name,
                "status": exec.status.value,
                "current_step": exec.current_step_index + 1 if exec.current_step_index < len(exec.definition.steps) else len(exec.definition.steps),
                "total_steps": len(exec.definition.steps),
                "current_iteration": exec.current_iteration,
                "max_iterations": exec.definition.max_iterations,
                "started_at": exec.started_at,
                "errors": exec.errors,
            }

    def get_execution(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get execution details."""
        with self._lock:
            return self._executions.get(workflow_id)

    def _create_result(self, execution: WorkflowExecution) -> WorkflowResult:
        """Create result from execution."""
        steps_completed = sum(
            1 for s in execution.definition.steps
            if s.status == StepStatus.COMPLETED
        )
        duration = None
        if execution.started_at and execution.completed_at:
            duration = execution.completed_at - execution.started_at

        return WorkflowResult(
            workflow_id=execution.definition.id,
            status=execution.status,
            context=execution.context,
            steps_completed=steps_completed,
            total_steps=len(execution.definition.steps),
            iterations=execution.current_iteration,
            errors=execution.errors,
            duration_seconds=duration,
        )

    def list_executions(self) -> List[Dict[str, Any]]:
        """List all workflow executions."""
        with self._lock:
            return [
                self.get_workflow_status(wid)
                for wid in self._executions
            ]


# Global orchestrator instance
_orchestrator: Optional[WorkflowOrchestrator] = None
_orchestrator_lock = threading.Lock()


def get_orchestrator() -> WorkflowOrchestrator:
    """Get or create the global orchestrator."""
    global _orchestrator
    with _orchestrator_lock:
        if _orchestrator is None:
            _orchestrator = WorkflowOrchestrator()
        return _orchestrator


def reset_orchestrator():
    """Reset the global orchestrator (for testing)."""
    global _orchestrator
    with _orchestrator_lock:
        _orchestrator = None
