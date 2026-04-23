"""Tools for Coordinator Agent."""

import asyncio
from pathlib import Path
from typing import List, Optional

from core.models import (
    CodeIssue,
    ReviewResult,
    ReviewReport,
    ReviewRequest,
    WorkflowState,
)
from agents.linter.tools import lint_file
from agents.reviewer.tools import review_file
from agents.test_agent.tools import analyze_test_needs
from agents.fixer.tools import apply_fixes


async def orchestrate_review(request: ReviewRequest) -> ReviewReport:
    """
    Orchestrate a multi-agent code review.

    Args:
        request: Review request with paths and options

    Returns:
        Unified review report
    """
    results: List[ReviewResult] = []
    files = []

    # Collect all Python files
    for path_str in request.paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            files.append(str(path))
        elif path.is_dir():
            files.extend([str(f) for f in path.rglob("*.py") if "__pycache__" not in str(f)])

    # Run agents in parallel
    tasks = []
    for file_path in files:
        tasks.append(_run_linter(file_path))
        tasks.append(_run_reviewer(file_path))
        if request.include_complexity:
            tasks.append(_run_test_agent(file_path))

    # Execute all tasks
    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in task_results:
        if isinstance(result, ReviewResult):
            results.append(result)
        elif isinstance(result, Exception):
            # Log error but continue
            pass

    # Create report
    report = ReviewReport.from_results(results, len(files))

    # Apply fixes if requested
    if request.auto_fix and report.summary.auto_fixed > 0:
        fix_results = await _apply_fixes(files, report.details)
        report.summary.auto_fixed = len(fix_results)

    return report


async def _run_linter(file_path: str) -> ReviewResult:
    """Run linter on a file."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lint_file, file_path)


async def _run_reviewer(file_path: str) -> ReviewResult:
    """Run reviewer on a file."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, review_file, file_path)


async def _run_test_agent(file_path: str) -> ReviewResult:
    """Run test agent on a file."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, analyze_test_needs, file_path)


async def _apply_fixes(files: List[str], issues: List[CodeIssue]) -> List[ReviewResult]:
    """Apply fixes to files."""
    tasks = []
    for file_path in files:
        file_issues = [i for i in issues if i.file == file_path and i.auto_fixable]
        if file_issues:
            loop = asyncio.get_event_loop()
            tasks.append(loop.run_in_executor(None, apply_fixes, file_path, file_issues))

    if tasks:
        return await asyncio.gather(*tasks, return_exceptions=True)
    return []


def aggregate_results(results: List[ReviewResult]) -> dict:
    """
    Aggregate results from multiple agents.

    Args:
        results: List of ReviewResult objects

    Returns:
        Aggregated summary dictionary
    """
    summary = {
        "total_issues": 0,
        "by_agent": {},
        "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "by_type": {},
        "auto_fixable": 0,
    }

    for result in results:
        if result.status != "success":
            continue

        if result.agent not in summary["by_agent"]:
            summary["by_agent"][result.agent] = 0
        summary["by_agent"][result.agent] += len(result.issues)

        for issue in result.issues:
            summary["total_issues"] += 1
            summary["by_severity"][issue.severity.value] += 1

            if issue.issue_type.value not in summary["by_type"]:
                summary["by_type"][issue.issue_type.value] = 0
            summary["by_type"][issue.issue_type.value] += 1

            if issue.auto_fixable:
                summary["auto_fixable"] += 1

    return summary


def generate_report(report: ReviewReport, include_details: bool = True) -> str:
    """
    Generate a formatted review report.

    Args:
        report: ReviewReport object
        include_details: Whether to include detailed issue list

    Returns:
        Formatted report string
    """
    output = []
    output.append("=" * 60)
    output.append("CODE REVIEW REPORT")
    output.append("=" * 60)
    output.append(f"\nTimestamp: {report.timestamp.isoformat()}")
    output.append(f"Files reviewed: {report.files_reviewed}")
    output.append(f"Agents used: {', '.join(report.agents_used)}")

    output.append("\n" + "-" * 40)
    output.append("SUMMARY")
    output.append("-" * 40)
    output.append(f"Total issues: {report.summary.total_issues}")
    output.append(f"  Critical: {report.summary.critical}")
    output.append(f"  High: {report.summary.high}")
    output.append(f"  Medium: {report.summary.medium}")
    output.append(f"  Low: {report.summary.low}")
    output.append(f"Auto-fixable: {report.summary.auto_fixed}")

    if include_details and report.details:
        output.append("\n" + "-" * 40)
        output.append("DETAILED ISSUES")
        output.append("-" * 40)

        # Group by file
        by_file = {}
        for issue in report.details:
            if issue.file not in by_file:
                by_file[issue.file] = []
            by_file[issue.file].append(issue)

        for file_path, issues in by_file.items():
            output.append(f"\n{Path(file_path).name}:")
            for issue in issues[:10]:  # Show first 10 per file
                output.append(
                    f"  [{issue.severity.value.upper():8}] "
                    f"Line {issue.line or '?':>4}: {issue.message}"
                )
            if len(issues) > 10:
                output.append(f"  ... and {len(issues) - 10} more issues")

    return "\n".join(output)