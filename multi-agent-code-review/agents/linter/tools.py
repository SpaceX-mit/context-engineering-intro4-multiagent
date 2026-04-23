"""Tools for Linter Agent."""

from typing import List

from tools.ast_analyzer import analyze_python_code, analyze_python_file
from tools.linter_tools import run_ruff_check, check_code_style
from core.models import CodeIssue, ReviewResult


def lint_file(file_path: str) -> ReviewResult:
    """
    Lint a Python file for style and formatting issues.

    Args:
        file_path: Path to the Python file

    Returns:
        ReviewResult with detected issues
    """
    issues: List[CodeIssue] = []

    # Run AST analysis
    ast_issues = analyze_python_file(file_path)
    issues.extend(ast_issues)

    # Run ruff check
    ruff_issues = run_ruff_check(file_path)
    issues.extend(ruff_issues)

    # Check code style
    try:
        with open(file_path, "r") as f:
            source = f.read()
        style_issues = check_code_style(source)
        # Convert style issues to CodeIssue if needed
    except Exception:
        pass

    summary = f"Found {len(issues)} linting issues"
    if issues:
        fixable = sum(1 for i in issues if i.auto_fixable)
        summary += f" ({fixable} auto-fixable)"

    return ReviewResult(
        agent="linter",
        issues=issues,
        summary=summary,
        status="success",
    )


def check_unused_imports(source: str, file_path: str = "") -> List[CodeIssue]:
    """
    Check for unused imports in Python source.

    Args:
        source: Python source code
        file_path: Optional file path for reference

    Returns:
        List of unused import issues
    """
    return analyze_python_code(source, file_path)


def check_style(source: str) -> dict:
    """
    Check code style compliance.

    Args:
        source: Python source code

    Returns:
        Dictionary with style check results
    """
    return check_code_style(source)


def analyze_lint_result(result: ReviewResult) -> str:
    """
    Analyze lint result and provide summary.

    Args:
        result: ReviewResult from linting

    Returns:
        Summary string
    """
    if not result.issues:
        return "No linting issues found."

    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    auto_fixable = 0

    for issue in result.issues:
        by_severity[issue.severity.value] += 1
        if issue.auto_fixable:
            auto_fixable += 1

    summary = f"Linting found {len(result.issues)} issues:\n"
    summary += f"- Critical: {by_severity['critical']}\n"
    summary += f"- High: {by_severity['high']}\n"
    summary += f"- Medium: {by_severity['medium']}\n"
    summary += f"- Low: {by_severity['low']}\n"
    summary += f"- Auto-fixable: {auto_fixable}"

    return summary