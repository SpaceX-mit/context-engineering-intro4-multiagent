"""Workflow orchestration for AI Coder."""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .prompts import (
    create_planner_prompt,
    create_coder_prompt,
    create_reviewer_prompt,
    create_tester_prompt,
    create_fixer_prompt,
)
from .tools import (
    execute_code,
    run_tests,
    extract_code_blocks,
    validate_code_syntax,
)


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in the workflow."""
    name: str
    description: str
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class AICoderResult:
    """Result of AI Coder workflow."""
    success: bool
    plan: Optional[str] = None
    code: Optional[str] = None
    review: Optional[str] = None
    tests: Optional[str] = None
    execution_output: Optional[str] = None
    error: Optional[str] = None
    steps: List[WorkflowStep] = field(default_factory=list)


class AICoderWorkflow:
    """
    Multi-agent workflow for AI Coder.

    Steps:
    1. Planning - Create implementation plan
    2. Coding - Generate code
    3. Review - Check for issues
    4. Testing - Run and verify
    5. Fixing - Resolve any issues
    """

    def __init__(self, agent=None):
        self.agent = agent
        self.steps: List[WorkflowStep] = []

    async def run(self, requirement: str, max_iterations: int = 2) -> AICoderResult:
        """
        Run the full workflow.

        Args:
            requirement: User's requirement
            max_iterations: Maximum fix iterations

        Returns:
            AICoderResult with all step results
        """
        result = AICoderResult(success=False)
        self.steps = []

        # Step 1: Planning
        plan_step = await self._run_planning(requirement)
        self.steps.append(plan_step)
        result.steps.append(plan_step)

        if plan_step.status == StepStatus.FAILED:
            result.error = f"Planning failed: {plan_step.error}"
            return result

        # Step 2: Coding
        code_step = await self._run_coding(plan_step.result)
        self.steps.append(code_step)
        result.steps.append(code_step)

        if code_step.status == StepStatus.FAILED:
            result.error = f"Coding failed: {code_step.error}"
            return result

        result.code = code_step.result

        # Step 3: Review
        review_step = await self._run_review(code_step.result)
        self.steps.append(review_step)
        result.steps.append(review_step)

        result.review = review_step.result

        # Step 4: Testing
        test_step = await self._run_testing(code_step.result)
        self.steps.append(test_step)
        result.steps.append(test_step)

        result.tests = test_step.result

        # Check if fixes needed
        issues = self._extract_issues(review_step.result, test_step.result)

        if issues and max_iterations > 0:
            # Step 5: Fixing (iterative)
            for i in range(max_iterations):
                fix_step = await self._run_fixing(code_step.result, issues)
                self.steps.append(fix_step)

                if fix_step.status == StepStatus.COMPLETED:
                    result.code = fix_step.result
                    # Re-test after fix
                    retest_step = await self._run_testing(fix_step.result)
                    self.steps.append(retest_step)
                    if retest_step.status == StepStatus.COMPLETED:
                        result.tests = retest_step.result
                        break

        # Run final execution
        exec_step = await self._run_execution(result.code)
        self.steps.append(exec_step)
        result.steps.append(exec_step)
        result.execution_output = exec_step.result

        result.success = True
        return result

    async def _run_planning(self, requirement: str) -> WorkflowStep:
        """Run planning step."""
        step = WorkflowStep(
            name="Planning",
            description="Creating implementation plan"
        )
        step.status = StepStatus.RUNNING
        start = time.time()

        try:
            if self.agent:
                prompt = create_planner_prompt(requirement)
                response = await self.agent.run(prompt)
                step.result = response.output if hasattr(response, "output") else str(response)
            else:
                step.result = f"# Plan for: {requirement}\n\n1. Create main.py\n2. Add functionality\n3. Test"
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

        step.duration = time.time() - start
        return step

    async def _run_coding(self, plan: str) -> WorkflowStep:
        """Run coding step."""
        step = WorkflowStep(
            name="Coding",
            description="Generating code"
        )
        step.status = StepStatus.RUNNING
        start = time.time()

        try:
            if self.agent:
                prompt = create_coder_prompt(plan)
                response = await self.agent.run(prompt)
                raw_code = response.output if hasattr(response, "output") else str(response)
                # Extract code blocks
                code_blocks = extract_code_blocks(raw_code)
                step.result = code_blocks[0] if code_blocks else raw_code
            else:
                step.result = "# Generated code here"
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

        step.duration = time.time() - start
        return step

    async def _run_review(self, code: str) -> WorkflowStep:
        """Run review step."""
        step = WorkflowStep(
            name="Review",
            description="Reviewing code quality"
        )
        step.status = StepStatus.RUNNING
        start = time.time()

        try:
            # First validate syntax
            valid, error = validate_code_syntax(code)
            if not valid:
                step.result = f"Syntax Error: {error}"
                step.status = StepStatus.COMPLETED
                step.duration = time.time() - start
                return step

            if self.agent:
                prompt = create_reviewer_prompt(code)
                response = await self.agent.run(prompt)
                step.result = response.output if hasattr(response, "output") else str(response)
            else:
                step.result = "Code looks good. No critical issues found."
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

        step.duration = time.time() - start
        return step

    async def _run_testing(self, code: str) -> WorkflowStep:
        """Run testing step."""
        step = WorkflowStep(
            name="Testing",
            description="Running tests"
        )
        step.status = StepStatus.RUNNING
        start = time.time()

        try:
            # First try to execute the code
            exec_result = execute_code(code)
            if exec_result["success"]:
                step.result = f"✓ Code executed successfully\n\nOutput:\n{exec_result['stdout']}"
            else:
                error_info = exec_result.get("error", {})
                step.result = f"✗ Execution failed:\n{error_info.get('message', 'Unknown error')}"
                if exec_result.get("stderr"):
                    step.result += f"\n\nStderr:\n{exec_result['stderr']}"

            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

        step.duration = time.time() - start
        return step

    async def _run_fixing(self, code: str, issues: str) -> WorkflowStep:
        """Run fixing step."""
        step = WorkflowStep(
            name="Fixing",
            description="Fixing code issues"
        )
        step.status = StepStatus.RUNNING
        start = time.time()

        try:
            if self.agent:
                prompt = create_fixer_prompt(code, issues)
                response = await self.agent.run(prompt)
                raw_code = response.output if hasattr(response, "output") else str(response)
                code_blocks = extract_code_blocks(raw_code)
                step.result = code_blocks[0] if code_blocks else raw_code
            else:
                step.result = code  # No fix without agent
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

        step.duration = time.time() - start
        return step

    async def _run_execution(self, code: str) -> WorkflowStep:
        """Run final execution."""
        step = WorkflowStep(
            name="Execution",
            description="Final code execution"
        )
        step.status = StepStatus.RUNNING
        start = time.time()

        try:
            exec_result = execute_code(code)
            if exec_result["success"]:
                step.result = exec_result["stdout"] or "(No output)"
            else:
                error_info = exec_result.get("error", {})
                step.result = f"Error: {error_info.get('message', 'Unknown')}"
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

        step.duration = time.time() - start
        return step

    def _extract_issues(self, review: str, test_result: str) -> str:
        """Extract issues from review and test results."""
        issues = []

        if review and "error" in review.lower():
            issues.append(review)
        if test_result and "✗" in test_result:
            issues.append(test_result)

        return "\n".join(issues) if issues else ""


async def run_full_workflow(requirement: str, agent=None) -> AICoderResult:
    """
    Convenience function to run the full workflow.

    Args:
        requirement: User requirement
        agent: Optional agent for LLM calls

    Returns:
        AICoderResult with all results
    """
    workflow = AICoderWorkflow(agent)
    return await workflow.run(requirement)


def format_result_markdown(result: AICoderResult) -> str:
    """
    Format result as markdown for display.

    Args:
        result: AICoderResult to format

    Returns:
        Markdown formatted string
    """
    output = []

    output.append("# 🧠 AI Coder Result\n")

    # Show step progress
    output.append("## Progress\n")
    for step in result.steps:
        icon = {
            StepStatus.COMPLETED: "✅",
            StepStatus.RUNNING: "⏳",
            StepStatus.FAILED: "❌",
            StepStatus.PENDING: "⭕",
            StepStatus.SKIPPED: "⏭️",
        }.get(step.status, "❓")

        duration = f"({step.duration:.2f}s)" if step.duration else ""
        output.append(f"{icon} **{step.name}** - {step.description} {duration}")

    output.append("")

    # Show plan
    if result.plan:
        output.append("## 📋 Plan\n")
        output.append(result.plan)
        output.append("")

    # Show code
    if result.code:
        output.append("## 💻 Generated Code\n")
        output.append(f"```python\n{result.code}\n```")
        output.append("")

    # Show review
    if result.review:
        output.append("## 🔍 Review\n")
        output.append(result.review)
        output.append("")

    # Show execution output
    if result.execution_output:
        output.append("## ▶️ Execution Output\n")
        output.append(f"```\n{result.execution_output}\n```")
        output.append("")

    # Show error if any
    if result.error:
        output.append(f"## ❌ Error\n{result.error}")

    return "\n".join(output)