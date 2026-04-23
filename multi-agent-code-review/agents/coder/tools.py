"""Tools for Coder Agent."""

import ast
from pathlib import Path
from typing import List, Optional

from core.models import CodeIssue, Severity, IssueType


def generate_code_from_requirement(
    requirement: str,
    language: str = "python",
) -> str:
    """
    Generate code based on a requirement description.

    Args:
        requirement: Description of what the code should do
        language: Programming language (default: python)

    Returns:
        Generated code as string
    """
    # This will be handled by the LLM
    return f"# Generated code for: {requirement}"


def validate_code(code: str) -> List[CodeIssue]:
    """
    Validate generated code for basic correctness.

    Args:
        code: Python code to validate

    Returns:
        List of issues found
    """
    issues: List[CodeIssue] = []

    try:
        ast.parse(code)
    except SyntaxError as e:
        issues.append(
            CodeIssue(
                file="",
                line=e.lineno,
                column=e.offset,
                severity=Severity.CRITICAL,
                issue_type=IssueType.CORRECTNESS,
                message=f"Syntax error: {e.msg}",
                auto_fixable=False,
                rule_id="E999",
            )
        )

    return issues


def suggest_tests(code: str, test_framework: str = "pytest") -> str:
    """
    Suggest tests for the given code.

    Args:
        code: Python code to write tests for
        test_framework: Testing framework to use

    Returns:
        Test code as string
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "# Cannot parse code for test generation"

    # Extract functions and classes
    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not node.name.startswith("_"):
                functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

    # Generate test template
    tests = []

    if test_framework == "pytest":
        tests.append('"""Tests for the generated code."""')
        tests.append("import pytest\n")

        for func in functions:
            tests.append(f"\n\ndef test_{func}():")
            tests.append(f'    """Test {func}."""')
            tests.append("    # TODO: Add test implementation")
            tests.append("    pass")

        for cls in classes:
            tests.append(f"\n\nclass Test{cls}:")
            tests.append(f'    """Tests for {cls}."""')
            tests.append("\n    def test_initialization(self):")
            tests.append(f'        """Test {cls} initialization."""')
            tests.append("        # TODO: Add test implementation")
            tests.append("        pass")

    return "\n".join(tests)


def format_code(code: str) -> str:
    """
    Format code according to style guidelines.

    Args:
        code: Python code to format

    Returns:
        Formatted code
    """
    # Basic formatting - real implementation would use black or ruff
    lines = code.split("\n")
    formatted_lines = []

    for line in lines:
        # Remove trailing whitespace
        line = line.rstrip()
        formatted_lines.append(line)

    return "\n".join(formatted_lines)


def extract_dependencies(code: str) -> List[str]:
    """
    Extract import statements from code.

    Args:
        code: Python code to analyze

    Returns:
        List of import statements
    """
    imports: List[str] = []

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    if alias.name == "*":
                        imports.append(f"{module}.*")
                    else:
                        imports.append(f"{module}.{alias.name}")

    except SyntaxError:
        pass

    return imports


def analyze_code_structure(code: str) -> dict:
    """
    Analyze the structure of Python code.

    Args:
        code: Python code to analyze

    Returns:
        Dictionary with structure information
    """
    result = {
        "functions": [],
        "classes": [],
        "imports": [],
        "complexity": 0,
    }

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": len(node.args.args),
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })

            elif isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, ast.FunctionDef)
                ]
                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                })

        result["imports"] = extract_dependencies(code)

    except SyntaxError:
        pass

    return result
