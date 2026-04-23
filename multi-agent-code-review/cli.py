"""CLI interface for multi-agent code review."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.models import ReviewRequest
from core.workflow import WorkflowType, run_workflow, batch_review_workflow
from agents.coordinator.tools import orchestrate_review, generate_report


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Multi-Agent Code Review System.

    A production-ready multi-agent system for automated code review.
    """
    pass


@cli.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--workflow",
    "-w",
    type=click.Choice(["sequential", "concurrent", "iterative"]),
    default="concurrent",
    help="Workflow type to use",
)
@click.option(
    "--auto-fix",
    "-f",
    is_flag=True,
    help="Automatically fix issues",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--max-iterations",
    "-i",
    default=3,
    help="Maximum iterations for iterative workflow",
)
def review(
    paths: tuple,
    workflow: str,
    auto_fix: bool,
    output: str,
    max_iterations: int,
):
    """Review code files or directories.

    Examples:
        python -m multi_agent_code_review.cli review file.py
        python -m multi_agent_code_review.cli review file1.py file2.py
        python -m multi_agent_code_review.cli review --workflow iterative --auto-fix src/
    """
    # Convert paths to list
    path_list = list(paths)

    # Collect all Python files
    files = []
    for path_str in path_list:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            files.append(str(path))
        elif path.is_dir():
            py_files = [
                str(f)
                for f in path.rglob("*.py")
                if "__pycache__" not in str(f) and not f.name.startswith("test_")
            ]
            files.extend(py_files)

    if not files:
        click.echo("Error: No Python files found to review.")
        sys.exit(1)

    # Determine workflow type
    workflow_type = WorkflowType.SEQUENTIAL
    if workflow == "concurrent":
        workflow_type = WorkflowType.CONCURRENT
    elif workflow == "iterative":
        workflow_type = WorkflowType.ITERATIVE

    # Run review
    click.echo(f"Reviewing {len(files)} file(s) with {workflow} workflow...")

    try:
        reports = asyncio.run(
            batch_review_workflow(
                files,
                workflow_type=workflow_type,
                parallel=True,
            )
        )

        # Generate output
        if output == "json":
            output_data = {
                "files_reviewed": len(files),
                "workflow": workflow,
                "reports": [r.to_dict() for r in reports],
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            for i, report in enumerate(reports):
                file_name = Path(files[i]).name
                click.echo(f"\n{'=' * 50}")
                click.echo(f"File: {file_name}")
                click.echo(f"{'=' * 50}")
                click.echo(f"Issues found: {report.summary.total_issues}")
                click.echo(f"  Critical: {report.summary.critical}")
                click.echo(f"  High: {report.summary.high}")
                click.echo(f"  Medium: {report.summary.medium}")
                click.echo(f"  Low: {report.summary.low}")
                click.echo(f"Auto-fixed: {report.summary.auto_fixed}")

        # Apply fixes if requested
        if auto_fix:
            click.echo("\nAuto-fix not implemented yet. Use ruff --fix manually.")

    except Exception as e:
        click.echo(f"Error during review: {e}")
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def quick(file_path: str):
    """Quick review of a single file.

    Example:
        python -m multi_agent_code_review.cli quick file.py
    """
    try:
        result = asyncio.run(run_workflow(file_path, WorkflowType.CONCURRENT))

        click.echo(f"Quick Review: {Path(file_path).name}")
        click.echo(f"{'=' * 40}")
        click.echo(f"Issues found: {result.summary.total_issues}")
        click.echo(f"  Critical: {result.summary.critical}")
        click.echo(f"  High: {result.summary.high}")
        click.echo(f"  Medium: {result.summary.medium}")
        click.echo(f"  Low: {result.summary.low}")

    except Exception as e:
        click.echo(f"Error during review: {e}")
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def lint(file_path: str):
    """Run only the linter on a file.

    Example:
        python -m multi_agent_code_review.cli lint file.py
    """
    from agents.linter.tools import lint_file

    try:
        result = asyncio.run(asyncio.to_thread(lint_file, file_path))

        click.echo(f"Linter results for: {Path(file_path).name}")
        click.echo(f"{'=' * 40}")

        if not result.issues:
            click.echo("No linting issues found.")
        else:
            click.echo(f"Found {len(result.issues)} issues:")
            for issue in result.issues:
                click.echo(
                    f"  Line {issue.line or '?'}: {issue.message}"
                    f" [{issue.severity.value}]"
                )

    except Exception as e:
        click.echo(f"Error during linting: {e}")
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def security(file_path: str):
    """Run only the security scanner on a file.

    Example:
        python -m multi_agent_code_review.cli security file.py
    """
    from agents.reviewer.tools import detect_security_issues

    try:
        result = asyncio.run(asyncio.to_thread(detect_security_issues, file_path))

        click.echo(f"Security scan for: {Path(file_path).name}")
        click.echo(f"{'=' * 40}")

        if not result.issues:
            click.echo("No security issues found.")
        else:
            click.echo(f"Found {len(result.issues)} security issues:")
            for issue in result.issues:
                click.echo(
                    f"  Line {issue.line or '?'}: {issue.message}"
                    f" [{issue.severity.value}]"
                )

    except Exception as e:
        click.echo(f"Error during security scan: {e}")
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def coverage(file_path: str):
    """Analyze test coverage for a file.

    Example:
        python -m multi_agent_code_review.cli coverage file.py
    """
    from agents.test_agent.tools import analyze_coverage

    try:
        result = asyncio.run(asyncio.to_thread(analyze_coverage, file_path))

        click.echo(f"Test coverage analysis for: {Path(file_path).name}")
        click.echo(f"{'=' * 40}")
        click.echo(f"Has tests: {'Yes' if result.get('has_tests') else 'No'}")
        click.echo(f"Coverage: {result.get('coverage_percentage', 0):.0f}%")

        if result.get("missing_test_types"):
            click.echo("\nMissing test types:")
            for test_type in result["missing_test_types"]:
                click.echo(f"  - {test_type}")

    except Exception as e:
        click.echo(f"Error during coverage analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()