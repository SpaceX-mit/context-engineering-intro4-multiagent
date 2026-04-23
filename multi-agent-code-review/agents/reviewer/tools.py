"""Tools for Reviewer Agent."""

import ast
from typing import List

from tools.ast_analyzer import calculate_complexity
from tools.security_scanner import scan_security_issues, run_bandit_scan
from core.models import CodeIssue, Severity, IssueType, ReviewResult


def analyze_complexity(source: str, file_path: str = "") -> dict:
    """
    Analyze code complexity.

    Args:
        source: Python source code
        file_path: Optional file path

    Returns:
        Dictionary with complexity metrics
    """
    result = {
        "file": file_path,
        "functions": [],
        "classes": [],
        "max_complexity": 0,
        "average_complexity": 0,
        "issues": [],
    }

    try:
        tree = ast.parse(source)

        total_complexity = 0
        count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = calculate_complexity(node)
                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "complexity": complexity,
                })
                total_complexity += complexity
                count += 1
                result["max_complexity"] = max(result["max_complexity"], complexity)

                if complexity > 10:
                    result["issues"].append(
                        CodeIssue(
                            file=file_path,
                            line=node.lineno,
                            column=None,
                            severity=Severity.MEDIUM,
                            issue_type=IssueType.COMPLEXITY,
                            message=f"Function '{node.name}' has high complexity ({complexity})",
                            suggestion="Consider refactoring into smaller functions",
                            auto_fixable=False,
                            rule_id="C901",
                        )
                    )

            elif isinstance(node, ast.ClassDef):
                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": sum(1 for m in node.body if isinstance(m, ast.FunctionDef)),
                })

        if count > 0:
            result["average_complexity"] = total_complexity / count

    except SyntaxError:
        result["issues"].append(
            CodeIssue(
                file=file_path,
                line=1,
                column=None,
                severity=Severity.CRITICAL,
                issue_type=IssueType.CORRECTNESS,
                message="Syntax error preventing analysis",
                suggestion="Fix syntax errors before analysis",
                auto_fixable=False,
                rule_id="E999",
            )
        )

    return result


def detect_security_issues(file_path: str) -> ReviewResult:
    """
    Detect security issues in Python code.

    Args:
        file_path: Path to the Python file

    Returns:
        ReviewResult with security issues
    """
    issues: List[CodeIssue] = []

    # Run Bandit scanner
    bandit_issues = run_bandit_scan(file_path)
    issues.extend(bandit_issues)

    # Also run our own checks
    try:
        with open(file_path, "r") as f:
            source = f.read()
        custom_issues = scan_security_issues(source, file_path)
        issues.extend(custom_issues)
    except Exception:
        pass

    summary = f"Found {len(issues)} security issues"
    if issues:
        high_severity = sum(1 for i in issues if i.severity == Severity.HIGH)
        if high_severity > 0:
            summary += f" ({high_severity} high severity)"

    return ReviewResult(
        agent="reviewer",
        issues=issues,
        summary=summary,
        status="success" if issues else "success",
    )


def assess_maintainability(source: str, file_path: str = "") -> dict:
    """
    Assess code maintainability.

    Args:
        source: Python source code
        file_path: Optional file path

    Returns:
        Dictionary with maintainability assessment
    """
    result = {
        "file": file_path,
        "score": 100,
        "issues": [],
        "recommendations": [],
    }

    lines = source.split("\n")

    # Check line length
    long_lines = sum(1 for line in lines if len(line) > 120)
    if long_lines > 0:
        result["score"] -= long_lines * 0.5
        result["recommendations"].append(f"Consider breaking {long_lines} long lines (>120 chars)")

    # Check for missing docstrings
    try:
        tree = ast.parse(source)
        public_funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
        if len(public_funcs) > 5:
            result["recommendations"].append("Consider adding module-level documentation")
    except Exception:
        pass

    # Check for TODO comments
    todo_count = sum(1 for line in lines if "TODO" in line or "FIXME" in line)
    if todo_count > 0:
        result["recommendations"].append(f"Address {todo_count} TODO/FIXME comments")

    # Check for deep nesting
    max_nesting = 0
    for line in lines:
        nesting = len(line) - len(line.lstrip())
        max_nesting = max(max_nesting, nesting // 4)

    if max_nesting > 4:
        result["score"] -= (max_nesting - 4) * 2
        result["recommendations"].append(f"Reduce deep nesting (max: {max_nesting} levels)")

    result["score"] = max(0, min(100, result["score"]))

    return result


def review_file(file_path: str) -> ReviewResult:
    """
    Perform full code review on a file.

    Args:
        file_path: Path to the Python file

    Returns:
        ReviewResult with all issues found
    """
    issues: List[CodeIssue] = []

    # Read the file
    try:
        with open(file_path, "r") as f:
            source = f.read()
    except Exception as e:
        return ReviewResult(
            agent="reviewer",
            issues=[],
            summary=f"Error reading file: {e}",
            status="error",
        )

    # Complexity analysis
    complexity_result = analyze_complexity(source, file_path)
    issues.extend(complexity_result.get("issues", []))

    # Security scan
    security_result = detect_security_issues(file_path)
    issues.extend(security_result.issues)

    # Maintainability assessment
    maintain_result = assess_maintainability(source, file_path)

    summary = f"Review found {len(issues)} issues"
    if maintain_result["score"] < 80:
        summary += f" | Maintainability score: {maintain_result['score']:.0f}/100"

    return ReviewResult(
        agent="reviewer",
        issues=issues,
        summary=summary,
        status="success",
    )