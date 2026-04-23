"""Test coverage analysis tools."""

import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set


def analyze_test_coverage(file_path: str, test_path: Optional[str] = None) -> dict:
    """
    Analyze test coverage for a Python file.

    Args:
        file_path: Path to the Python file
        test_path: Path to the test file (optional, will be auto-detected)

    Returns:
        Dictionary with coverage analysis
    """
    result = {
        "file": file_path,
        "has_tests": False,
        "coverage_percentage": 0.0,
        "uncovered_functions": [],
        "uncovered_branches": [],
        "missing_test_types": [],
    }

    # Check if test file exists
    if test_path is None:
        test_path = _find_test_file(file_path)

    if test_path and Path(test_path).exists():
        result["has_tests"] = True

        # Run coverage
        coverage_data = _run_coverage(file_path, test_path)
        result.update(coverage_data)
    else:
        # Analyze what tests would be needed
        result["missing_test_types"] = _suggest_tests_needed(file_path)

    return result


def _find_test_file(file_path: str) -> Optional[str]:
    """Find corresponding test file for a Python file."""
    path = Path(file_path)

    # Check common test directory patterns
    test_dirs = ["tests", "test", "spec", "__tests__"]

    # Get module path
    module_path = path.stem

    # Handle __init__.py files
    if module_path == "__init__":
        module_path = path.parent.name

    # Check test directories in same parent
    parent = path.parent
    for test_dir in test_dirs:
        test_parent = parent / test_dir
        if test_parent.exists():
            # Check for test_FILE.py or FILE_test.py patterns
            for pattern in [f"test_{module_path}.py", f"{module_path}_test.py"]:
                test_file = test_parent / pattern
                if test_file.exists():
                    return str(test_file)

    # Check parent of parent
    if parent.parent.exists():
        for test_dir in test_dirs:
            test_grandparent = parent.parent / test_dir
            if test_grandparent.exists():
                for pattern in [f"test_{module_path}.py", f"{module_path}_test.py"]:
                    test_file = test_grandparent / pattern
                    if test_file.exists():
                        return str(test_file)

    return None


def _run_coverage(file_path: str, test_path: str) -> dict:
    """Run coverage.py on a file."""
    result = {
        "coverage_percentage": 0.0,
        "uncovered_functions": [],
        "uncovered_branches": [],
    }

    try:
        # Run coverage with pytest
        process = subprocess.run(
            ["coverage", "run", "-m", "pytest", test_path, "--tb=no", "-q"],
            capture_output=True,
            text=True,
            cwd=Path(file_path).parent,
        )

        # Get coverage report
        report = subprocess.run(
            ["coverage", "report", "--include", str(file_path)],
            capture_output=True,
            text=True,
        )

        # Parse coverage output
        for line in report.stdout.split("\n"):
            if Path(file_path).name in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        # Extract percentage
                        coverage_str = parts[-1].replace("%", "")
                        result["coverage_percentage"] = float(coverage_str)
                    except (ValueError, IndexError):
                        pass

    except FileNotFoundError:
        # Coverage not installed
        pass
    except Exception:
        pass

    return result


def _suggest_tests_needed(file_path: str) -> List[str]:
    """Suggest what tests are needed for a file."""
    suggestions: List[str] = []

    try:
        with open(file_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        # Check for functions without tests
        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        # Suggest test types
        if functions:
            suggestions.append(f"Unit tests for {len(functions)} function(s)")
        if classes:
            suggestions.append(f"Class tests for {len(classes)} class(es)")
            suggestions.append("Integration tests for class interactions")

        # Check for common patterns
        if "async" in source:
            suggestions.append("Async/await tests")
        if "database" in source.lower() or "db" in source.lower():
            suggestions.append("Database integration tests")
        if "api" in source.lower() or "http" in source.lower():
            suggestions.append("API endpoint tests")

    except Exception:
        suggestions.append("General unit tests")

    return suggestions


def identify_boundary_conditions(file_path: str) -> List[dict]:
    """
    Identify potential boundary conditions that should be tested.

    Args:
        file_path: Path to the Python file

    Returns:
        List of boundary conditions to test
    """
    conditions: List[dict] = []

    try:
        with open(file_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Check comparison operations
                for op in node.ops:
                    if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                        conditions.append(
                            {
                                "type": "comparison",
                                "description": f"Boundary check: {op}",
                                "line": node.lineno,
                            }
                        )

            elif isinstance(node, ast.If):
                # Check for edge case patterns
                if isinstance(node.test, ast.BoolOp):
                    conditions.append(
                        {
                            "type": "boolean_logic",
                            "description": "Complex boolean condition",
                            "line": node.lineno,
                        }
                    )

    except Exception:
        pass

    return conditions


def generate_test_suggestions(issues: List) -> List[str]:
    """
    Generate test suggestions based on code issues.

    Args:
        issues: List of CodeIssue objects

    Returns:
        List of test suggestions
    """
    suggestions: List[str] = []

    for issue in issues:
        if issue.issue_type.value == "security":
            suggestions.append(f"Security test for: {issue.rule_id}")

    # Add general suggestions
    suggestions.append("Edge case tests for error handling")
    suggestions.append("Performance tests for critical paths")
    suggestions.append("Integration tests for external dependencies")

    return list(set(suggestions))  # Remove duplicates