"""Tools modules for code analysis."""

from .ast_analyzer import analyze_python_code, analyze_python_file, count_lines_of_code
from .linter_tools import lint_python_code
from .security_scanner import scan_security_issues
from .code_analysis import analyze_code_structure

# Aliases for convenience
lint_code = lint_python_code
security_scan = scan_security_issues

__all__ = [
    "analyze_python_code",
    "analyze_python_file",
    "count_lines_of_code",
    "lint_code",
    "lint_python_code",
    "security_scan",
    "scan_security_issues",
    "analyze_code_structure",
]