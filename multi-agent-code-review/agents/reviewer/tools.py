"""Tools for the Reviewer Agent."""

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.context import CodeIssue, Severity


@dataclass
class ReviewResult:
    """Result of code review."""
    code: str
    issues: List[CodeIssue] = field(default_factory=list)
    score: int = 100  # 0-100
    summary: str = ""


def review_code(code: str) -> ReviewResult:
    """
    Review code for issues.

    Args:
        code: Python code to review

    Returns:
        Review result with issues
    """
    result = ReviewResult(code=code)
    result.issues = []

    # Syntax check
    try:
        ast.parse(code)
    except SyntaxError as e:
        result.issues.append(CodeIssue(
            line=e.lineno,
            severity=Severity.CRITICAL,
            issue_type="syntax",
            message=f"Syntax error: {e.msg}",
            auto_fixable=False,
        ))
        result.score -= 50
        return result

    # Check for basic patterns
    lines = code.split('\n')

    for i, line in enumerate(lines, 1):
        # Check for TODO without error handling
        if "TODO" in line or "FIXME" in line:
            result.issues.append(CodeIssue(
                line=i,
                severity=Severity.MEDIUM,
                issue_type="completeness",
                message="TODO/FIXME found - needs implementation",
                auto_fixable=False,
            ))
            result.score -= 5

        # Check for print statements in functions
        if re.match(r'\s*print\(', line) and 'def ' not in line:
            # Only flag if not in main block
            if i > len(lines) - 5:
                result.issues.append(CodeIssue(
                    line=i,
                    severity=Severity.LOW,
                    issue_type="style",
                    message="Consider using logging instead of print",
                    auto_fixable=False,
                ))
                result.score -= 2

        # Check for bare except
        if re.match(r'\s*except\s*:', line):
            result.issues.append(CodeIssue(
                line=i,
                severity=Severity.HIGH,
                issue_type="error_handling",
                message="Bare except clause - catches all exceptions",
                suggestion="Use 'except Exception as e:' instead",
                auto_fixable=False,
            ))
            result.score -= 10

        # Check for division without zero check
        if '/' in line and 'divide' in code.lower():
            # Check if there are zero checks nearby
            context = '\n'.join(lines[max(0, i-3):i+3])
            if 'zero' not in context.lower() and '== 0' not in context:
                result.issues.append(CodeIssue(
                    line=i,
                    severity=Severity.HIGH,
                    issue_type="logic",
                    message="Potential division by zero - add validation",
                    suggestion="Check divisor != 0 before dividing",
                    auto_fixable=False,
                ))
                result.score -= 15

    # Check for missing docstrings
    functions = re.findall(r'def\s+(\w+)\s*\(', code)
    if functions:
        for func in functions:
            pattern = rf'def {func}\s*\([^)]*\):[^#]*"""[^"]*"""'
            if not re.search(pattern, code):
                result.issues.append(CodeIssue(
                    line=1,
                    severity=Severity.LOW,
                    issue_type="documentation",
                    message=f"Function '{func}' may be missing docstring",
                    auto_fixable=False,
                ))
                result.score -= 3

    # Ensure score doesn't go negative
    result.score = max(0, result.score)

    # Generate summary
    critical = len([i for i in result.issues if i.severity == Severity.CRITICAL])
    high = len([i for i in result.issues if i.severity == Severity.HIGH])
    medium = len([i for i in result.issues if i.severity == Severity.MEDIUM])
    low = len([i for i in result.issues if i.severity == Severity.LOW])

    result.summary = f"Found {len(result.issues)} issues: {critical} critical, {high} high, {medium} medium, {low} low"

    return result


def check_security(code: str) -> List[CodeIssue]:
    """Check for security issues."""
    issues = []
    lines = code.split('\n')

    for i, line in enumerate(lines, 1):
        # Check for hardcoded secrets
        if any(kw in line.lower() for kw in ['password', 'secret', 'api_key', 'token']):
            if '=' in line and not line.strip().startswith('#'):
                issues.append(CodeIssue(
                    line=i,
                    severity=Severity.CRITICAL,
                    issue_type="security",
                    message="Potential hardcoded secret detected",
                    suggestion="Use environment variables instead",
                    auto_fixable=False,
                ))

        # Check for SQL injection risk
        if 'execute' in line and 'f"' in line or 'execute' in line and '%' in line:
            issues.append(CodeIssue(
                line=i,
                severity=Severity.CRITICAL,
                issue_type="security",
                message="Potential SQL injection vulnerability",
                suggestion="Use parameterized queries",
                auto_fixable=False,
            ))

    return issues


def format_review_report(result: ReviewResult) -> str:
    """Format review result as a readable report."""
    output = f"## Code Review Report\n\n"
    output += f"**Score:** {result.score}/100\n"
    output += f"**Issues:** {len(result.issues)}\n\n"

    if result.issues:
        # Group by severity
        by_severity = {}
        for issue in result.issues:
            sev = issue.severity.value
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(issue)

        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                output += f"### {severity.upper()}\n"
                for issue in by_severity[severity]:
                    output += f"- Line {issue.line}: {issue.message}\n"
                    if issue.suggestion:
                        output += f"  - Suggestion: {issue.suggestion}\n"
                output += "\n"

    return output
