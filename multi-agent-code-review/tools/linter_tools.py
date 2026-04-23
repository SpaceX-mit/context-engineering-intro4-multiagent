"""Ruff-based linting tools."""

import json
import subprocess
from pathlib import Path
from typing import List, Optional

from core.models import CodeIssue, Severity, IssueType


def run_ruff_check(
    file_path: str,
    config_path: Optional[str] = None,
    fix: bool = False,
) -> List[CodeIssue]:
    """
    Run ruff linter on a file.

    Args:
        file_path: Path to the file to lint
        config_path: Optional path to ruff configuration
        fix: Whether to auto-fix issues

    Returns:
        List of CodeIssue objects
    """
    issues: List[CodeIssue] = []

    cmd = ["ruff", "check", file_path]
    if fix:
        cmd.append("--fix")
    if config_path:
        cmd.extend(["--config", config_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Parse ruff output
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            # Parse ruff JSON output
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    issues.append(_parse_ruff_issue(data, file_path))
                except json.JSONDecodeError:
                    pass

        # Also parse text output format
        for line in result.stderr.split("\n"):
            if not line.strip():
                continue

            issue = _parse_ruff_text_output(line, file_path)
            if issue:
                issues.append(issue)

    except FileNotFoundError:
        # ruff not installed, return empty list
        pass
    except Exception:
        pass

    return issues


def _parse_ruff_issue(data: dict, file_path: str) -> CodeIssue:
    """Parse ruff JSON output to CodeIssue."""
    location = data.get("location", {})
    end_location = data.get("end_location", {})

    code = data.get("code", "")
    severity = _map_ruff_severity(data.get("severity", ""))

    return CodeIssue(
        file=file_path,
        line=location.get("line"),
        column=location.get("column"),
        severity=severity,
        issue_type=IssueType.LINT,
        message=data.get("message", ""),
        suggestion=data.get("fix", {}).get("message") if "fix" in data else None,
        auto_fixable="fix" in data,
        rule_id=code,
    )


def _parse_ruff_text_output(line: str, file_path: str) -> Optional[CodeIssue]:
    """Parse ruff text output to CodeIssue."""
    # Format: path:line:col: code: message
    if ":" not in line:
        return None

    parts = line.split(":")
    if len(parts) < 4:
        return None

    try:
        path = parts[0]
        line_num = int(parts[1])
        col = int(parts[2])
        rest = ":".join(parts[3:])

        # Extract code and message
        if " " in rest:
            code_end = rest.index(" ")
            code = rest[:code_end].strip()
            message = rest[code_end + 1 :].strip()
        else:
            code = ""
            message = rest

        return CodeIssue(
            file=file_path,
            line=line_num,
            column=col,
            severity=Severity.MEDIUM,
            issue_type=IssueType.LINT,
            message=message,
            auto_fixable=False,
            rule_id=code,
        )
    except (ValueError, IndexError):
        return None


def _map_ruff_severity(severity: str) -> Severity:
    """Map ruff severity to Severity enum."""
    severity_lower = severity.lower()
    if "error" in severity_lower:
        return Severity.HIGH
    elif "warning" in severity_lower:
        return Severity.MEDIUM
    else:
        return Severity.LOW


def lint_python_code(source: str, file_path: str = "") -> List[CodeIssue]:
    """
    Lint Python code using ruff.

    Args:
        source: Python source code
        file_path: Path to save and lint (optional)

    Returns:
        List of CodeIssue objects
    """
    issues: List[CodeIssue] = []

    # If file_path provided, lint directly
    if file_path and Path(file_path).exists():
        issues.extend(run_ruff_check(file_path))
    else:
        # Create temporary file for linting
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
        ) as f:
            f.write(source)
            temp_path = f.name

        try:
            issues.extend(run_ruff_check(temp_path))
        finally:
            Path(temp_path).unlink(missing_ok=True)

    return issues


def check_code_style(source: str) -> dict:
    """
    Check code style issues.

    Args:
        source: Python source code

    Returns:
        Dictionary with style check results
    """
    results = {
        "has_trailing_whitespace": any(line.rstrip() != line for line in source.split("\n")),
        "has_tabs": any("\t" in line for line in source.split("\n")),
        "line_length_violations": [],
        "missing_docstrings": [],
    }

    # Check line length
    for i, line in enumerate(source.split("\n"), 1):
        if len(line) > 100:
            results["line_length_violations"].append({"line": i, "length": len(line)})

    return results