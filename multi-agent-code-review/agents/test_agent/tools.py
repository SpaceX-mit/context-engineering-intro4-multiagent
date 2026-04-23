"""Tools for Test Agent."""

from typing import List

from tools.coverage_analyzer import (
    analyze_test_coverage,
    identify_boundary_conditions,
    generate_test_suggestions,
)
from core.models import ReviewResult, CodeIssue, Severity, IssueType


def analyze_coverage(file_path: str) -> dict:
    """
    Analyze test coverage for a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Dictionary with coverage analysis
    """
    return analyze_test_coverage(file_path)


def suggest_tests(file_path: str) -> List[str]:
    """
    Suggest missing test cases for a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        List of test suggestions
    """
    # Get coverage analysis
    coverage = analyze_test_coverage(file_path)

    suggestions = []

    # Add suggestions from coverage analysis
    if coverage.get("missing_test_types"):
        suggestions.extend(coverage["missing_test_types"])

    # Get boundary conditions
    boundaries = identify_boundary_conditions(file_path)
    if boundaries:
        suggestions.append(f"Test {len(boundaries)} boundary conditions identified")

    # Generate additional suggestions
    suggestions.extend(generate_test_suggestions([]))

    return suggestions


def analyze_test_needs(file_path: str) -> ReviewResult:
    """
    Analyze test needs for a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        ReviewResult with test coverage analysis
    """
    issues: List[CodeIssue] = []

    # Get coverage analysis
    coverage = analyze_test_coverage(file_path)

    # Add issues for uncovered functions
    for func in coverage.get("uncovered_functions", []):
        issues.append(
            CodeIssue(
                file=file_path,
                line=func.get("line"),
                column=None,
                severity=Severity.MEDIUM,
                issue_type=IssueType.TEST,
                message=f"Function '{func['name']}' is not covered by tests",
                suggestion="Add test cases for this function",
                auto_fixable=False,
                rule_id="T001",
            )
        )

    # Add issue if no tests exist
    if not coverage.get("has_tests"):
        issues.append(
            CodeIssue(
                file=file_path,
                line=None,
                column=None,
                severity=Severity.HIGH,
                issue_type=IssueType.TEST,
                message="No test file found for this module",
                suggestion=f"Create a test file (test_{file_path.split('/')[-1]})",
                auto_fixable=False,
                rule_id="T000",
            )
        )

    summary = f"Test coverage: {coverage.get('coverage_percentage', 0):.0f}%"
    if coverage.get("missing_test_types"):
        summary += f" | Missing: {', '.join(coverage['missing_test_types'][:2])}"

    return ReviewResult(
        agent="test_agent",
        issues=issues,
        summary=summary,
        status="success",
    )


def generate_test_template(file_path: str) -> str:
    """
    Generate a test file template for a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Test file template as string
    """
    import ast
    from pathlib import Path

    template = '"""Tests for {module_name}."""\n\n'
    template += "import pytest\n"
    template += "\n\n"

    try:
        with open(file_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)
        module_name = Path(file_path).stem

        template += f"# Import the module to test\n"
        template += f"from {module_name} import *\n\n"

        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                functions.append(node)
            elif isinstance(node, ast.ClassDef):
                classes.append(node)

        # Add test class for each class
        for cls in classes:
            template += f"\n\nclass Test{cls.name}:\n"
            template += f'    """Tests for {cls.name}."""\n\n'
            template += f"    def test_initialization(self):\n"
            template += f'        """Test {cls.name} initialization."""\n'
            template += f"        # TODO: Add test\n"
            template += f"        pass\n"

        # Add test functions for each function
        for func in functions:
            template += f"\n\ndef test_{func.name}():\n"
            template += f'    """Test {func.name}."""\n'
            template += f"    # TODO: Add test\n"
            template += f"    pass\n"

    except Exception as e:
        template += f"# Error parsing file: {e}\n"

    return template