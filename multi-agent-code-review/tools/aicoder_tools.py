"""AI Coder specific tools - Execution utilities.

Note: Main tools are in tools/__init__.py
This module provides additional AI Coder-specific utilities.
"""

from typing import Dict, List, Optional, Any
import io
import sys
import re


class OutputCapture:
    """Capture stdout during code execution."""

    def __init__(self):
        self.output = io.StringIO()
        self._old_stdout = None

    def __enter__(self):
        self._old_stdout = sys.stdout
        sys.stdout = self.output
        return self

    def __exit__(self, *args):
        sys.stdout = self._old_stdout

    def get_output(self) -> str:
        return self.output.getvalue()


def execute_code_safe(code: str) -> Dict[str, Any]:
    """Execute Python code safely.

    Args:
        code: Python code to execute

    Returns:
        Dict with success, output, error
    """
    with OutputCapture() as capture:
        try:
            namespace = {
                "__name__": "__aicoder__",
                "__builtins__": {
                    "print": print, "len": len, "range": range, "str": str,
                    "int": int, "float": float, "list": list, "dict": dict,
                    "set": set, "tuple": tuple, "bool": bool,
                    "True": True, "False": False, "None": None,
                    "enumerate": enumerate, "zip": zip, "sorted": sorted,
                    "sum": sum, "min": min, "max": max, "abs": abs,
                },
            }
            exec(code, namespace)
            return {"success": True, "output": capture.get_output(), "error": None}
        except Exception as e:
            return {"success": False, "output": capture.get_output(), "error": str(e)}


def extract_code_blocks(text: str) -> List[str]:
    """Extract Python code blocks from markdown text."""
    pattern = r'```python\n([\s\S]*?)```'
    matches = re.findall(pattern, text)
    return [m.strip() for m in matches if m.strip()]


def validate_code_syntax(code: str) -> Dict[str, Any]:
    """Validate Python code syntax."""
    try:
        compile(code, '<string>', 'exec')
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {"valid": False, "error": str(e)}


def run_tests(code: str, test_code: str) -> Dict[str, Any]:
    """Run tests against code."""
    # Combine code and tests
    combined = code + "\n\n" + test_code

    result = execute_code_safe(combined)

    # Parse pytest output
    output = result.get("output", "")
    passed = "passed" in output.lower()
    failed = "failed" in output.lower()

    return {
        "success": result["success"],
        "passed": passed and not failed,
        "output": output,
        "error": result.get("error"),
    }


def format_markdown_output(title: str, content: str, language: str = "") -> str:
    """Format output as markdown."""
    lang_tag = f"```{language}\n" if language else "```\n"
    return f"## {title}\n\n{lang_tag}{content}```"


__all__ = [
    "OutputCapture",
    "execute_code_safe",
    "extract_code_blocks",
    "validate_code_syntax",
    "run_tests",
    "format_markdown_output",
]