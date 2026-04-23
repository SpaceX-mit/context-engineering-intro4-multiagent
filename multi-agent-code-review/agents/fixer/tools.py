"""Tools for Fixer Agent."""

import ast
import re
from pathlib import Path
from typing import List, Tuple

from core.models import CodeIssue, Severity, IssueType, ReviewResult


def fix_imports(source: str) -> Tuple[str, List[CodeIssue]]:
    """
    Remove unused imports from Python source.

    Args:
        source: Python source code

    Returns:
        Tuple of (fixed source, list of issues fixed)
    """
    issues_fixed: List[CodeIssue] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, []

    # Track used names
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    # Find and remove unused imports
    lines = source.split("\n")
    new_lines = []
    import_lines_to_remove = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for import statements
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Extract imported names
            if stripped.startswith("import "):
                names = [n.strip() for n in stripped[7:].split(",")]
            else:  # from ... import
                match = re.search(r"import\s+(.+)", stripped)
                if match:
                    names = [n.strip() for n in match.group(1).split(",")]
                else:
                    names = []

            # Check if any names are used
            unused = []
            for name in names:
                # Handle "import X as Y"
                base_name = name.split(" as ")[0].strip()
                if base_name not in used_names:
                    unused.append(name)

            if unused and len(unused) == len(names):
                # All imports unused, remove line
                issues_fixed.append(
                    CodeIssue(
                        file="",
                        line=i + 1,
                        column=0,
                        severity=Severity.LOW,
                        issue_type=IssueType.LINT,
                        message=f"Removed unused import: {stripped}",
                        suggestion=None,
                        auto_fixable=True,
                        rule_id="F401",
                    )
                )
                import_lines_to_remove.append(i)
                continue

        new_lines.append(line)

    return "\n".join(new_lines), issues_fixed


def fix_style_issues(source: str, issues: List[CodeIssue]) -> Tuple[str, List[CodeIssue]]:
    """
    Fix style issues in Python source.

    Args:
        source: Python source code
        issues: List of issues to fix

    Returns:
        Tuple of (fixed source, list of issues fixed)
    """
    lines = source.split("\n")
    fixed_lines = list(lines)
    issues_fixed: List[CodeIssue] = []

    for issue in issues:
        if not issue.auto_fixable:
            continue

        if issue.line is None or issue.line > len(lines):
            continue

        line_idx = issue.line - 1
        line = lines[line_idx]

        # Handle specific rule IDs
        if issue.rule_id == "E501":  # Line too long
            # Try to split the line
            new_lines = split_long_line(line)
            if new_lines:
                fixed_lines[line_idx:line_idx + 1] = new_lines
                issues_fixed.append(issue)

        elif issue.rule_id == "F401":  # Unused import
            # Already handled by fix_imports
            pass

        elif issue.rule_id == "F841":  # Unused variable
            # Add underscore prefix
            new_line = add_underscore_prefix(line)
            if new_line:
                fixed_lines[line_idx] = new_line
                issues_fixed.append(issue)

    return "\n".join(fixed_lines), issues_fixed


def split_long_line(line: str) -> List[str]:
    """Split a long line into multiple lines."""
    # Simple heuristic: split at commas or operators
    if len(line) <= 100:
        return [line]

    result = []
    indent = len(line) - len(line.lstrip())

    # Try splitting at comma
    if "," in line:
        parts = line.split(",")
        current = parts[0]
        for part in parts[1:]:
            if len(current) + len(part) + 2 > 100:
                result.append(current + ",")
                current = " " * (indent + 4) + part.strip()
            else:
                current += "," + part
        if current:
            result.append(current)

    return result if result else [line]


def add_underscore_prefix(line: str) -> str:
    """Add underscore prefix to unused variable."""
    # Match assignment patterns
    match = re.match(r"^(\s*)(\w+)(\s*=.*)$", line)
    if match:
        indent, name, rest = match.groups()
        if not name.startswith("_"):
            return f"{indent}_{name}{rest}"
    return ""


def verify_fix(original: str, fixed: str) -> dict:
    """
    Verify that a fix doesn't break the code.

    Args:
        original: Original source code
        fixed: Fixed source code

    Returns:
        Dictionary with verification result
    """
    result = {
        "valid": False,
        "syntax_ok": False,
        "changes": 0,
    }

    # Check syntax
    try:
        ast.parse(fixed)
        result["syntax_ok"] = True
    except SyntaxError as e:
        result["error"] = str(e)
        return result

    # Count changes
    result["changes"] = sum(
        1 for o, f in zip(original.split("\n"), fixed.split("\n")) if o != f
    )

    result["valid"] = True
    return result


def apply_fixes(file_path: str, issues: List[CodeIssue]) -> ReviewResult:
    """
    Apply fixes to a Python file.

    Args:
        file_path: Path to the Python file
        issues: List of issues to fix

    Returns:
        ReviewResult with applied fixes
    """
    try:
        with open(file_path, "r") as f:
            source = f.read()
    except Exception as e:
        return ReviewResult(
            agent="fixer",
            issues=[],
            summary=f"Error reading file: {e}",
            status="error",
        )

    original = source
    issues_fixed: List[CodeIssue] = []

    # First fix imports
    fixed, import_fixes = fix_imports(source)
    issues_fixed.extend(import_fixes)

    # Then fix other style issues
    fixed, style_fixes = fix_style_issues(fixed, issues)
    issues_fixed.extend(style_fixes)

    # Verify fix
    verification = verify_fix(original, fixed)

    if not verification["valid"]:
        return ReviewResult(
            agent="fixer",
            issues=[],
            summary=f"Fix verification failed: {verification.get('error', 'Unknown error')}",
            status="error",
        )

    # Write fixed code
    if verification["changes"] > 0:
        with open(file_path, "w") as f:
            f.write(fixed)

    summary = f"Applied {len(issues_fixed)} fixes"
    if verification["changes"] > 0:
        summary += f" ({verification['changes']} lines changed)"

    return ReviewResult(
        agent="fixer",
        issues=issues_fixed,
        summary=summary,
        status="success",
    )