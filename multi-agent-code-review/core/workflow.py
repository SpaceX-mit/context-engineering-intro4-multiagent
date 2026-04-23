"""Workflow orchestration for multi-agent code review.

This module implements the workflow patterns from agent-framework:
- Sequential workflow: Linter -> Review -> Fix
- Concurrent workflow: Multiple agents analyze in parallel
- Iterative workflow: Review -> Fix -> Review (loop until clean)
"""

import asyncio
from enum import Enum
from typing import List, Optional

from core.models import (
    CodeIssue,
    ReviewRequest,
    ReviewReport,
    ReviewResult,
    WorkflowState,
)
from agents.linter.tools import lint_file
from agents.reviewer.tools import review_file
from agents.test_agent.tools import analyze_test_needs
from agents.fixer.tools import apply_fixes


class WorkflowType(Enum):
    """Type of workflow to execute."""

    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    ITERATIVE = "iterative"


async def sequential_review_workflow(
    file_path: str,
    include_tests: bool = True,
) -> ReviewReport:
    """
    Run sequential review: Linter -> Review -> Fix.

    Args:
        file_path: Path to the Python file
        include_tests: Whether to include test analysis

    Returns:
        Review report with all issues found
    """
    results: List[ReviewResult] = []

    # Step 1: Linter
    linter_result = await asyncio.to_thread(lint_file, file_path)
    results.append(linter_result)

    # Step 2: Reviewer
    reviewer_result = await asyncio.to_thread(review_file, file_path)
    results.append(reviewer_result)

    # Step 3: Test Agent (optional)
    if include_tests:
        test_result = await asyncio.to_thread(analyze_test_needs, file_path)
        results.append(test_result)

    # Create report
    return ReviewReport.from_results(results, 1)


async def concurrent_review_workflow(
    file_path: str,
    include_tests: bool = True,
) -> ReviewReport:
    """
    Run concurrent review: All agents analyze in parallel.

    Args:
        file_path: Path to the Python file
        include_tests: Whether to include test analysis

    Returns:
        Review report with all issues found
    """
    # Create all tasks
    tasks = [
        asyncio.to_thread(lint_file, file_path),
        asyncio.to_thread(review_file, file_path),
    ]

    if include_tests:
        tasks.append(asyncio.to_thread(analyze_test_needs, file_path))

    # Run in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    valid_results: List[ReviewResult] = []
    for result in results:
        if isinstance(result, ReviewResult):
            valid_results.append(result)

    # Create report
    return ReviewReport.from_results(valid_results, 1)


async def iterative_review_workflow(
    file_path: str,
    max_iterations: int = 3,
) -> ReviewReport:
    """
    Run iterative review: Review -> Fix -> Review (loop until clean).

    Args:
        file_path: Path to the Python file
        max_iterations: Maximum number of review-fix iterations

    Returns:
        Final review report after iterations
    """
    state = WorkflowState()
    all_issues: List[CodeIssue] = []

    for iteration in range(max_iterations):
        state.iterations = iteration + 1

        # Run review
        report = await concurrent_review_workflow(file_path, include_tests=False)

        # Collect issues
        all_issues.extend(report.details)

        # Check if we should continue
        if not report.details:
            state.status = "completed"
            break

        # Count issues that need fixing
        fixable_issues = [i for i in report.details if i.auto_fixable]
        if not fixable_issues:
            # No more auto-fixable issues
            break

        # Apply fixes
        await asyncio.to_thread(apply_fixes, file_path, fixable_issues)

    # Create final report
    return ReviewReport(
        files_reviewed=1,
        details=all_issues,
        agents_used=["linter", "reviewer"],
    )


async def run_workflow(
    file_path: str,
    workflow_type: WorkflowType = WorkflowType.CONCURRENT,
    max_iterations: int = 3,
    include_tests: bool = True,
) -> ReviewReport:
    """
    Run a code review workflow.

    Args:
        file_path: Path to the Python file
        workflow_type: Type of workflow to run
        max_iterations: Maximum iterations for iterative workflow
        include_tests: Whether to include test analysis

    Returns:
        Review report
    """
    if workflow_type == WorkflowType.SEQUENTIAL:
        return await sequential_review_workflow(file_path, include_tests)
    elif workflow_type == WorkflowType.ITERATIVE:
        return await iterative_review_workflow(file_path, max_iterations)
    else:
        return await concurrent_review_workflow(file_path, include_tests)


async def batch_review_workflow(
    file_paths: List[str],
    workflow_type: WorkflowType = WorkflowType.CONCURRENT,
    parallel: bool = True,
) -> List[ReviewReport]:
    """
    Run review on multiple files.

    Args:
        file_paths: List of file paths to review
        workflow_type: Type of workflow to run
        parallel: Whether to process files in parallel

    Returns:
        List of review reports
    """
    if parallel:
        tasks = [run_workflow(fp, workflow_type) for fp in file_paths]
        return await asyncio.gather(*tasks)
    else:
        results = []
        for fp in file_paths:
            result = await run_workflow(fp, workflow_type)
            results.append(result)
        return results


class WorkflowBuilder:
    """
    Builder for custom workflows.

    This follows the WorkflowBuilder pattern from agent-framework.
    """

    def __init__(self):
        self._agents: List[str] = []
        self._workflow_type = WorkflowType.CONCURRENT
        self._max_iterations = 3
        self._include_tests = True

    def add_agent(self, agent_name: str) -> "WorkflowBuilder":
        """Add an agent to the workflow."""
        self._agents.append(agent_name)
        return self

    def with_sequential(self) -> "WorkflowBuilder":
        """Set workflow to sequential mode."""
        self._workflow_type = WorkflowType.SEQUENTIAL
        return self

    def with_iterative(self, max_iterations: int = 3) -> "WorkflowBuilder":
        """Set workflow to iterative mode."""
        self._workflow_type = WorkflowType.ITERATIVE
        self._max_iterations = max_iterations
        return self

    def with_tests(self, include: bool = True) -> "WorkflowBuilder":
        """Set whether to include test analysis."""
        self._include_tests = include
        return self

    def build(self):
        """Build the workflow configuration."""
        return {
            "agents": self._agents,
            "workflow_type": self._workflow_type,
            "max_iterations": self._max_iterations,
            "include_tests": self._include_tests,
        }