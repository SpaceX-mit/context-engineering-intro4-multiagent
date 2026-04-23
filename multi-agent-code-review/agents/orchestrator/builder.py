"""Workflow builder patterns for multi-agent orchestration."""

from typing import List, Callable, Any, Dict
from enum import Enum


class WorkflowType(Enum):
    """Workflow types for multi-agent coordination."""
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    ITERATIVE = "iterative"
    GROUP_CHAT = "group_chat"


class SequentialBuilder:
    """Build sequential workflow where agents execute in order."""

    def __init__(self):
        self.steps: List[Callable] = []
        self.descriptions: List[str] = []

    def add_step(self, func: Callable, description: str = "") -> "SequentialBuilder":
        """Add a step to the workflow."""
        self.steps.append(func)
        self.descriptions.append(description or f"Step {len(self.steps)}")
        return self

    def build(self):
        """Build the workflow."""
        return SequentialWorkflow(self.steps, self.descriptions)


class SequentialWorkflow:
    """Sequential workflow executor."""

    def __init__(self, steps: List[Callable], descriptions: List[str]):
        self.steps = steps
        self.descriptions = descriptions

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow steps sequentially."""
        results = []
        for i, (step, desc) in enumerate(zip(self.steps, self.descriptions)):
            result = await step(context)
            results.append({"step": i + 1, "description": desc, "result": result})
        return {"steps": results, "final_result": results[-1] if results else None}

    def execute_sync(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow synchronously."""
        import asyncio
        return asyncio.run(self.execute(context))


class ConcurrentBuilder:
    """Build concurrent workflow where agents execute in parallel."""

    def __init__(self):
        self.tasks: List[Callable] = []
        self.descriptions: List[str] = []

    def add_task(self, func: Callable, description: str = "") -> "ConcurrentBuilder":
        """Add a task to the workflow."""
        self.tasks.append(func)
        self.descriptions.append(description or f"Task {len(self.tasks)}")
        return self

    def build(self):
        """Build the workflow."""
        return ConcurrentWorkflow(self.tasks, self.descriptions)


class ConcurrentWorkflow:
    """Concurrent workflow executor."""

    def __init__(self, tasks: List[Callable], descriptions: List[str]):
        self.tasks = tasks
        self.descriptions = descriptions

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow tasks concurrently."""
        import asyncio

        async def run_task(func, desc):
            return {"description": desc, "result": await func(context)}

        results = await asyncio.gather(*[
            run_task(task, desc) for task, desc in zip(self.tasks, self.descriptions)
        ])

        return {"tasks": results, "all_results": [r["result"] for r in results]}

    def execute_sync(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow synchronously."""
        import asyncio
        return asyncio.run(self.execute(context))


class IterativeBuilder:
    """Build iterative workflow for repeated refinement."""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.condition: Callable = None

    def set_condition(self, condition: Callable) -> "IterativeBuilder":
        """Set the condition for continuing iteration."""
        self.condition = condition
        return self

    def build(self):
        """Build the workflow."""
        return IterativeWorkflow(self.max_iterations, self.condition)


class IterativeWorkflow:
    """Iterative workflow executor."""

    def __init__(self, max_iterations: int, condition: Callable):
        self.max_iterations = max_iterations
        self.condition = condition

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow iteratively."""
        iterations = []
        for i in range(self.max_iterations):
            iteration_result = context.get("current_result")
            if self.condition and not self.condition(iteration_result):
                break
            iterations.append({
                "iteration": i + 1,
                "result": iteration_result
            })
        return {"iterations": iterations, "final_result": iterations[-1] if iterations else None}