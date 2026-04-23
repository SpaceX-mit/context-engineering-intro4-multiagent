"""AST-based code analysis tools."""

import ast
from typing import List, Optional, Set

from core.models import CodeIssue, Severity, IssueType


class UnusedImportVisitor(ast.NodeVisitor):
    """Visitor to detect unused imports."""

    def __init__(self) -> None:
        self.used_names: Set[str] = set()
        self.imports: List[tuple] = []
        self.issues: List[CodeIssue] = []
        self._in_function = False
        self._in_class = False

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            if alias.asname:
                self.imports.append((alias.asname, node.lineno, node.col_offset))
            else:
                self.imports.append((alias.name, node.lineno, node.col_offset))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from ... import statements."""
        module = node.module or ""
        for alias in node.names:
            if alias.asname:
                self.imports.append((alias.asname, node.lineno, node.col_offset))
            else:
                full_name = f"{module}.{alias.name}" if module else alias.name
                self.imports.append((alias.name, node.lineno, node.col_offset))

    def visit_Name(self, node: ast.Name) -> None:
        """Track used names."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function definitions."""
        self.used_names.add(node.name)
        self._in_function = True
        self.generic_visit(node)
        self._in_function = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function definitions."""
        self.used_names.add(node.name)
        self._in_function = True
        self.generic_visit(node)
        self._in_function = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class definitions."""
        self.used_names.add(node.name)
        self._in_class = True
        self.generic_visit(node)
        self._in_class = False

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.used_names.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Track annotated assignments."""
        if isinstance(node.target, ast.Name):
            self.used_names.add(target.id)
        self.generic_visit(node)

    def check_unused_imports(self) -> None:
        """Check and create issues for unused imports."""
        for name, line, col in self.imports:
            if name not in self.used_names:
                self.issues.append(
                    CodeIssue(
                        file="",
                        line=line,
                        column=col,
                        severity=Severity.MEDIUM,
                        issue_type=IssueType.LINT,
                        message=f"Unused import '{name}'",
                        suggestion=f"Remove the unused import '{name}'",
                        auto_fixable=True,
                        rule_id="F401",
                    )
                )


class UnusedVariableVisitor(ast.NodeVisitor):
    """Visitor to detect unused variables."""

    def __init__(self) -> None:
        self.issues: List[CodeIssue] = []
        self._local_names: Set[str] = set()
        self._scope_stack: List[Set[str]] = [set()]

    def _enter_scope(self) -> None:
        """Enter a new scope."""
        self._scope_stack.append(set())

    def _exit_scope(self) -> None:
        """Exit current scope and check for unused variables."""
        scope = self._scope_stack.pop()
        for name, line, col in scope:
            self.issues.append(
                CodeIssue(
                    file="",
                    line=line,
                    column=col,
                    severity=Severity.LOW,
                    issue_type=IssueType.LINT,
                    message=f"Unused variable '{name}'",
                    suggestion=f"Remove or use the variable '{name}'",
                    auto_fixable=False,
                    rule_id="F841",
                )
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                if len(node.targets) == 1:
                    self._scope_stack[-1].add((target.id, node.lineno, node.col_offset))
        self.generic_visit(node)


def analyze_python_code(source: str, file_path: str = "") -> List[CodeIssue]:
    """
    Analyze Python source code and return issues.

    Args:
        source: Python source code to analyze
        file_path: Path to the file being analyzed

    Returns:
        List of CodeIssue objects
    """
    issues: List[CodeIssue] = []

    try:
        tree = ast.parse(source, filename=file_path)

        # Check for unused imports
        import_visitor = UnusedImportVisitor()
        import_visitor.visit(tree)
        import_visitor.check_unused_imports()

        for issue in import_visitor.issues:
            issue.file = file_path
            issues.append(issue)

    except SyntaxError as e:
        issues.append(
            CodeIssue(
                file=file_path,
                line=e.lineno,
                column=e.offset,
                severity=Severity.CRITICAL,
                issue_type=IssueType.CORRECTNESS,
                message=f"Syntax error: {e.msg}",
                suggestion="Fix the syntax error",
                auto_fixable=False,
                rule_id="E999",
            )
        )

    return issues


def analyze_python_file(file_path: str) -> List[CodeIssue]:
    """
    Analyze a Python file and return issues.

    Args:
        file_path: Path to the Python file

    Returns:
        List of CodeIssue objects
    """
    issues: List[CodeIssue] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        issues = analyze_python_code(source, file_path)

    except FileNotFoundError:
        issues.append(
            CodeIssue(
                file=file_path,
                line=None,
                column=None,
                severity=Severity.CRITICAL,
                issue_type=IssueType.CORRECTNESS,
                message=f"File not found: {file_path}",
                suggestion="Check the file path",
                auto_fixable=False,
                rule_id="E000",
            )
        )
    except Exception as e:
        issues.append(
            CodeIssue(
                file=file_path,
                line=None,
                column=None,
                severity=Severity.HIGH,
                issue_type=IssueType.CORRECTNESS,
                message=f"Error reading file: {str(e)}",
                suggestion="Check file permissions and content",
                auto_fixable=False,
                rule_id="E000",
            )
        )

    return issues


def count_lines_of_code(source: str) -> dict:
    """
    Count lines of code statistics.

    Args:
        source: Python source code

    Returns:
        Dictionary with line counts
    """
    lines = source.split("\n")
    total = len(lines)
    code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))
    comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
    blank_lines = total - code_lines - comment_lines

    return {
        "total": total,
        "code": code_lines,
        "comments": comment_lines,
        "blank": blank_lines,
    }


def calculate_complexity(node: ast.AST) -> int:
    """
    Calculate cyclomatic complexity of an AST.

    Args:
        node: AST node to analyze

    Returns:
        Complexity score
    """
    complexity = 1

    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1

    return complexity