"""Security scanning tools using Bandit."""

import json
import subprocess
from typing import List, Optional

from core.models import CodeIssue, Severity, IssueType


def run_bandit_scan(
    file_path: str,
    config_path: Optional[str] = None,
) -> List[CodeIssue]:
    """
    Run Bandit security scanner on a file.

    Args:
        file_path: Path to the file to scan
        config_path: Optional path to Bandit configuration

    Returns:
        List of CodeIssue objects
    """
    issues: List[CodeIssue] = []

    cmd = ["bandit", "-r", file_path, "-f", "json"]

    if config_path:
        cmd.extend(["-c", config_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Parse Bandit JSON output
        try:
            data = json.loads(result.stdout)
            for item in data.get("results", []):
                issues.append(_parse_bandit_issue(item))
        except json.JSONDecodeError:
            pass

    except FileNotFoundError:
        # Bandit not installed, return empty list
        pass
    except Exception:
        pass

    return issues


def _parse_bandit_issue(item: dict) -> CodeIssue:
    """Parse Bandit result to CodeIssue."""
    severity_map = {
        "LOW": Severity.LOW,
        "MEDIUM": Severity.MEDIUM,
        "HIGH": Severity.HIGH,
    }

    return CodeIssue(
        file=item.get("filename", ""),
        line=item.get("line_number"),
        column=None,
        severity=severity_map.get(item.get("issue_severity", "MEDIUM"), Severity.MEDIUM),
        issue_type=IssueType.SECURITY,
        message=item.get("issue_text", ""),
        suggestion=_get_bandit_fix_suggestion(item),
        auto_fixable=False,
        rule_id=item.get("test_id"),
    )


def _get_bandit_fix_suggestion(item: dict) -> str:
    """Get fix suggestion from Bandit issue."""
    test_name = item.get("test_name", "")

    # Common fix suggestions
    suggestions = {
        "B403": "Use 'markupsafe.markup' instead of 'markupsafe.Markup'",
        "B404": "Import subprocess only within the function that uses it",
        "B405": "Use 'importlib.util.spec_for_loader' instead of 'importlib.find_loader'",
        "B406": "Use 'importlib.util.find_spec' instead of 'pkg_resources.iter_entry_points'",
        "B407": "Use 'importlib.util.find_spec' instead of 'pkg_resources.WorkingSet.iter_entry_points'",
        "B410": "Use 'hashlib.blake2b' instead of 'hashlib.sha512' for password hashing",
        "B602": "subprocess call with shell=True identified, security issue.",
        "B603": "subprocess call without checking return code identified.",
        "B604": "subprocess call with shell=True identified.",
        "B605": "A nested Python shell was started.",
        "B606": "pickle.load called with no signature check.",
        "B607": "pickle.load called with known unsafe module.",
        "B608": "SQL query construction using string formatting detected.",
        "B609": "Linux password detection in file.",
        "B701": "XMLRPC server at 'port' is vulnerable to XXE attacks.",
        "B702": "Use of 'mako' templates vulnerable to XEE attacks.",
        "B703": "Use of 'django.utils.html.format_html' with string injection.",
    }

    return suggestions.get(test_name, "Review and fix this security issue")


def scan_security_issues(source: str, file_path: str = "") -> List[CodeIssue]:
    """
    Scan for security issues in Python code.

    Args:
        source: Python source code
        file_path: Optional path to file

    Returns:
        List of CodeIssue objects with security issues
    """
    issues: List[CodeIssue] = []

    # Check for common security patterns
    issues.extend(_check_sql_injection(source, file_path))
    issues.extend(_check_eval_usage(source, file_path))
    issues.extend(_check_pickle_usage(source, file_path))
    issues.extend(_check_hardcoded_passwords(source, file_path))

    return issues


def _check_sql_injection(source: str, file_path: str) -> List[CodeIssue]:
    """Check for SQL injection vulnerabilities."""
    issues: List[CodeIssue] = []
    lines = source.split("\n")

    for i, line in enumerate(lines, 1):
        # Check for string formatting in SQL queries
        if any(keyword in line.lower() for keyword in ["execute", "cursor.execute", "query"]):
            if any(op in line for op in ['"', "'", "%", "f'"]):
                # Potential SQL injection
                if "format" in line or "%" in line or 'f"' in line or "'.format" in line:
                    issues.append(
                        CodeIssue(
                            file=file_path,
                            line=i,
                            column=None,
                            severity=Severity.HIGH,
                            issue_type=IssueType.SECURITY,
                            message="Possible SQL injection - string formatting in query",
                            suggestion="Use parameterized queries instead of string formatting",
                            auto_fixable=False,
                            rule_id="B608",
                        )
                    )

    return issues


def _check_eval_usage(source: str, file_path: str) -> List[CodeIssue]:
    """Check for dangerous eval usage."""
    issues: List[CodeIssue] = []
    lines = source.split("\n")

    for i, line in enumerate(lines, 1):
        if "eval(" in line and "assert" not in line:
            issues.append(
                CodeIssue(
                    file=file_path,
                    line=i,
                    column=None,
                    severity=Severity.HIGH,
                    issue_type=IssueType.SECURITY,
                    message="Use of 'eval' is dangerous with user input",
                    suggestion="Avoid using eval with untrusted input",
                    auto_fixable=False,
                    rule_id="B102",
                )
            )

    return issues


def _check_pickle_usage(source: str, file_path: str) -> List[CodeIssue]:
    """Check for dangerous pickle usage."""
    issues: List[CodeIssue] = []
    lines = source.split("\n")

    for i, line in enumerate(lines, 1):
        if "pickle.load" in line or "pickle.loads" in line:
            issues.append(
                CodeIssue(
                    file=file_path,
                    line=i,
                    column=None,
                    severity=Severity.MEDIUM,
                    issue_type=IssueType.SECURITY,
                    message="Deserialization of untrusted data with pickle",
                    suggestion="Use a safer serialization format or validate input",
                    auto_fixable=False,
                    rule_id="B301",
                )
            )

    return issues


def _check_hardcoded_passwords(source: str, file_path: str) -> List[CodeIssue]:
    """Check for hardcoded passwords."""
    issues: List[CodeIssue] = []
    lines = source.split("\n")

    for i, line in enumerate(lines, 1):
        lower_line = line.lower()
        if "password" in lower_line or "secret" in lower_line:
            if "=" in line and ("'" in line or '"' in line):
                # Possible hardcoded password
                if "example" not in lower_line and "placeholder" not in lower_line:
                    issues.append(
                        CodeIssue(
                            file=file_path,
                            line=i,
                            column=None,
                            severity=Severity.HIGH,
                            issue_type=IssueType.SECURITY,
                            message="Possible hardcoded password or secret detected",
                            suggestion="Use environment variables or a secrets manager",
                            auto_fixable=False,
                            rule_id="B105",
                        )
                    )

    return issues