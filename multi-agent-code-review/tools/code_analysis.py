"""Code analysis tools."""

from .ast_analyzer import analyze_python_code, analyze_python_file, count_lines_of_code


def lint_code(code, language):
    """Stub for lint_code - not used in code_analysis."""
    return []


def security_scan(code, language):
    """Stub for security_scan - not used in code_analysis."""
    return []


__all__ = [
    "analyze_python_code",
    "analyze_python_file",
    "count_lines_of_code",
    "lint_code",
    "security_scan",
    "analyze_code_structure",
]


def analyze_code_structure(code: str, language: str = "python") -> dict:
    """Analyze code structure for review."""
    if language.lower() != "python":
        return {"error": "Only Python supported for structure analysis"}

    import ast

    try:
        tree = ast.parse(code)
        functions = []
        classes = []
        imports = []
        complexity = 1

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "args": len(node.args.args),
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "nested_depth": 0,
                }
                functions.append(func_info)

            elif isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body if isinstance(n, ast.FunctionDef)
                ]
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                })

            elif isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])

            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "unknown")

            elif isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "complexity": complexity,
        }
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}
    except Exception as e:
        return {"error": str(e)}