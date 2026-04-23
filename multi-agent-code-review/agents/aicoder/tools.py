"""Tools for AI Coder Agent."""

import io
import os
import sys
import tempfile
import traceback
from typing import Dict, List, Optional, Tuple


class OutputCapture:
    """Capture stdout/stderr during code execution."""

    def __init__(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.exception = None

    def __enter__(self):
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr
        if exc_type:
            self.exception = {
                "type": exc_type.__name__,
                "message": str(exc_val),
                "traceback": "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            }
        return False

    def get_output(self) -> str:
        return self.stdout.getvalue()

    def get_error(self) -> str:
        return self.stderr.getvalue()


def execute_code(code: str, timeout: int = 10) -> Dict:
    """
    Execute Python code safely and return results.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds

    Returns:
        Dict with stdout, stderr, exception, success
    """
    result = {
        "success": True,
        "stdout": "",
        "stderr": "",
        "error": None,
        "execution_time": 0,
    }

    import time
    start = time.time()

    try:
        with OutputCapture() as capture:
            # Create a restricted namespace
            namespace = {
                "__name__": "__aicoder__",
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "tuple": tuple,
                    "bool": bool,
                    "True": True,
                    "False": False,
                    "None": None,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "sorted": sorted,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "isinstance": isinstance,
                    "type": type,
                }
            }

            exec(code, namespace)

        result["stdout"] = capture.get_output()
        result["stderr"] = capture.get_error()

    except Exception as e:
        result["success"] = False
        result["error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": "".join(traceback.format_exception(type(e), e, e.__traceback__))
        }

    result["execution_time"] = time.time() - start
    return result


def run_tests(code: str, test_code: str) -> Dict:
    """
    Run test code against the main code.

    Args:
        code: Main code to test
        test_code: Test code to run

    Returns:
        Dict with test results
    """
    combined_code = f"{code}\n\n{test_code}"
    return execute_code(combined_code)


def validate_code_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Python code syntax without executing.

    Args:
        code: Python code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(code, "<string>", "exec")
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


def extract_code_blocks(text: str) -> List[str]:
    """
    Extract Python code blocks from markdown text.

    Args:
        text: Text containing code blocks

    Returns:
        List of code blocks
    """
    import re

    # Match ```python ... ``` or ``` ... ```
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    return [match.strip() for match in matches]


def save_to_file(filepath: str, content: str) -> Dict:
    """
    Save content to a file.

    Args:
        filepath: Path to save to
        content: Content to write

    Returns:
        Dict with success status
    """
    try:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "filepath": filepath}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_from_file(filepath: str) -> Dict:
    """
    Read content from a file.

    Args:
        filepath: Path to read

    Returns:
        Dict with content or error
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "content": content, "filepath": filepath}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_project_files(path: str = ".", extensions: List[str] = None) -> List[str]:
    """
    List files in a project directory.

    Args:
        path: Root directory to scan
        extensions: File extensions to include

    Returns:
        List of file paths
    """
    if extensions is None:
        extensions = [".py", ".js", ".ts", ".html", ".css", ".json", ".md"]

    files = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__", "node_modules", "venv", ".git"]]

        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, filename)
                files.append(filepath)

    return sorted(files)


def create_project_structure(name: str, template: str = "default") -> Dict:
    """
    Create a project directory structure.

    Args:
        name: Project name
        template: Template type (default, fastapi, etc.)

    Returns:
        Dict with created files
    """
    base_path = os.path.join(".", name)
    structure = {
        "default": [
            f"{name}/__init__.py",
            f"{name}/main.py",
            f"{name}/requirements.txt",
        ],
        "fastapi": [
            f"{name}/__init__.py",
            f"{name}/main.py",
            f"{name}/requirements.txt",
            f"{name}/models.py",
            f"{name}/routes.py",
        ],
    }

    files = structure.get(template, structure["default"])

    try:
        for filepath in files:
            full_path = os.path.join(".", filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                if filepath.endswith(".py"):
                    f.write(f"# {filepath}\n")
                elif filepath == "requirements.txt":
                    f.write("# Requirements\n")

        return {"success": True, "files": files, "base_path": base_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_markdown_output(title: str, content: str, code: str = None) -> str:
    """
    Format output in markdown.

    Args:
        title: Section title
        content: Description
        code: Optional code block

    Returns:
        Formatted markdown string
    """
    output = f"## {title}\n\n{content}\n"
    if code:
        output += f"\n```python\n{code}\n```\n"
    return output