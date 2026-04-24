"""Tools modules for multi-agent code development."""

import os
import subprocess
from typing import Dict, List, Optional

# Analysis tools
from .ast_analyzer import analyze_python_code, analyze_python_file, count_lines_of_code
from .linter_tools import lint_python_code
from .security_scanner import scan_security_issues
from .code_analysis import analyze_code_structure


def execute_code(code: str, timeout: int = 30) -> Dict[str, any]:
    """Execute Python code safely and return result.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dict with success status, output, and error info
    """
    import io
    import sys
    import tempfile

    stdout_c = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_c

    result = {"success": True, "output": "", "error": None}

    RESTRICTED_BUILTINS = {
        "print": print, "len": len, "range": range, "str": str,
        "int": int, "float": float, "list": list, "dict": dict,
        "set": set, "tuple": tuple, "bool": bool,
        "True": True, "False": False, "None": None,
        "enumerate": enumerate, "zip": zip, "sorted": sorted,
        "sum": sum, "min": min, "max": max, "abs": abs,
        "isinstance": isinstance, "type": type,
    }

    try:
        namespace = {"__name__": "__aicoder__", "__builtins__": RESTRICTED_BUILTINS}
        exec(code, namespace)
        result["output"] = stdout_c.getvalue()
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    finally:
        sys.stdout = old_stdout

    return result


def save_to_file(filepath: str, content: str) -> bool:
    """Save content to a file.

    Args:
        filepath: Path to the file
        content: Content to write

    Returns:
        True if successful
    """
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False


def read_file(filepath: str) -> Optional[str]:
    """Read content from a file.

    Args:
        filepath: Path to the file

    Returns:
        File content or None if error
    """
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def list_directory(path: str = ".") -> List[Dict[str, str]]:
    """List files in a directory.

    Args:
        path: Directory path

    Returns:
        List of file info dicts
    """
    try:
        files = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            is_dir = os.path.isdir(full_path)
            files.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "path": full_path,
            })
        return files
    except Exception as e:
        print(f"Error listing directory: {e}")
        return []


def create_project_structure(
    name: str,
    template: str = "default",
    base_path: str = "."
) -> Dict[str, any]:
    """Create a new project structure.

    Args:
        name: Project name
        template: Project template type
        base_path: Base directory path

    Returns:
        Dict with success status and created paths
    """
    import json

    project_path = os.path.join(base_path, name)

    templates = {
        "default": {
            "src": "",
            "tests": "",
            "requirements.txt": "",
            "README.md": f"# {name}\n\nProject description",
        },
        "flask": {
            "src/app.py": "# Flask application",
            "src/models.py": "# Database models",
            "tests/test_app.py": "# Tests",
            "requirements.txt": "flask\nflask-cors",
            "README.md": f"# {name} - Flask Application",
        },
    }

    created = []
    template_files = templates.get(template, templates["default"])

    try:
        os.makedirs(project_path, exist_ok=True)

        for file_path, content in template_files.items():
            full_path = os.path.join(project_path, file_path)

            # Create parent directories
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, 'w') as f:
                f.write(content)
            created.append(full_path)

        return {
            "success": True,
            "project_path": project_path,
            "files_created": created,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# Aliases for convenience
lint_code = lint_python_code
security_scan = scan_security_issues
run_code = execute_code

__all__ = [
    # Analysis
    "analyze_python_code",
    "analyze_python_file",
    "count_lines_of_code",
    "lint_code",
    "lint_python_code",
    "security_scan",
    "scan_security_issues",
    "analyze_code_structure",
    # Code execution
    "execute_code",
    "run_code",
    # File management
    "save_to_file",
    "read_file",
    "list_directory",
    # Project
    "create_project_structure",
]