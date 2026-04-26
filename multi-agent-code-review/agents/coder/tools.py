"""Tools for the Coder Agent."""

import re
from typing import Any, Dict, List, Optional


def generate_code(requirement: str, plan: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate code based on requirement.

    Args:
        requirement: User requirement
        plan: Optional implementation plan

    Returns:
        Generated code
    """
    req_lower = requirement.lower()

    # Generate based on keywords
    if "hello" in req_lower and "world" in req_lower:
        return '''def hello_world():
    """Print hello world message."""
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
'''

    if "calculator" in req_lower:
        return '''class Calculator:
    """Basic calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        self.result = a + b
        return self.result

    def subtract(self, a: float, b: float) -> float:
        """Subtract two numbers."""
        self.result = a - b
        return self.result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        self.result = a * b
        return self.result

    def divide(self, a: float, b: float) -> float:
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        self.result = a / b
        return self.result

    def clear(self):
        """Clear the result."""
        self.result = 0
'''

    if "function" in req_lower or "def" in req_lower:
        # Extract function name
        match = re.search(r'(?:function|def)\s+(\w+)', requirement, re.IGNORECASE)
        func_name = match.group(1) if match else "my_function"
        return f'''def {func_name}():
    """Description of {func_name}."""
    pass

if __name__ == "__main__":
    {func_name}()
'''

    if "class" in req_lower:
        match = re.search(r'class\s+(\w+)', requirement, re.IGNORECASE)
        class_name = match.group(1) if match else "MyClass"
        return f'''class {class_name}:
    """Description of {class_name}."""

    def __init__(self):
        pass
'''

    # Build plan header if plan is provided
    plan_header = ""
    if plan:
        plan_text = plan if isinstance(plan, str) else str(plan)
        plan_header = f"# Plan:\n"
        for line in plan_text.split("\n")[:20]:
            plan_header += f"#   {line}\n"
        plan_header += "#\n"

    # Default: simple script
    return plan_header + f'''# Script based on: {requirement}
# TODO: Implement

def main():
    print("{requirement}")

if __name__ == "__main__":
    main()
'''


def validate_code(code: str) -> Dict[str, Any]:
    """
    Validate generated code.

    Args:
        code: Python code to validate

    Returns:
        Validation result
    """
    issues = []

    # Check for basic syntax issues
    if "def " in code and ":" not in code.split("def ")[1][:50]:
        issues.append({"line": 0, "severity": "error", "message": "Missing colon in function definition"})

    if "class " in code and ":" not in code.split("class ")[1][:50]:
        issues.append({"line": 0, "severity": "error", "message": "Missing colon in class definition"})

    # Check for TODO comments
    if "TODO" in code or "FIXME" in code:
        issues.append({"line": 0, "severity": "warning", "message": "Code contains unfinished TODOs"})

    return {
        "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
        "issues": issues,
        "warnings": len([i for i in issues if i["severity"] == "warning"]),
    }
