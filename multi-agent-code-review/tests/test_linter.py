"""Tests for Linter Agent."""

import pytest

from tools.ast_analyzer import (
    analyze_python_code,
    analyze_python_file,
    count_lines_of_code,
)
from core.models import Severity, IssueType


class TestASTAnalyzer:
    """Test AST-based code analysis."""

    def test_detects_unused_import(self, sample_code):
        """Test that unused imports are detected."""
        issues = analyze_python_code(sample_code)

        # 'os' is imported but not used
        unused_os = [i for i in issues if "os" in i.message and i.rule_id == "F401"]
        assert len(unused_os) >= 1

    def test_handles_syntax_error(self):
        """Test that syntax errors are handled gracefully."""
        code = "def broken(()"
        issues = analyze_python_code(code)

        assert len(issues) == 1
        assert issues[0].severity == Severity.CRITICAL
        assert issues[0].issue_type == IssueType.CORRECTNESS

    def test_analyze_python_file(self, temp_python_file):
        """Test file analysis."""
        issues = analyze_python_file(temp_python_file)

        assert isinstance(issues, list)
        # Should detect unused imports
        assert len(issues) >= 1

    def test_count_lines_of_code(self, sample_code):
        """Test line counting."""
        result = count_lines_of_code(sample_code)

        assert "total" in result
        assert "code" in result
        assert result["total"] > 0
        assert result["code"] > 0


class TestLinterTools:
    """Test linter tools."""

    def test_lint_file(self, temp_python_file):
        """Test linting a Python file."""
        from agents.linter.tools import lint_file

        result = lint_file(temp_python_file)

        assert result.agent == "linter"
        assert result.status == "success"
        assert isinstance(result.issues, list)

    def test_check_unused_imports(self, sample_code):
        """Test unused import checking."""
        from agents.linter.tools import check_unused_imports

        issues = check_unused_imports(sample_code)

        assert isinstance(issues, list)
        # Should find unused 'os'
        os_issues = [i for i in issues if "os" in i.message]
        assert len(os_issues) >= 1

    def test_check_style(self, sample_code):
        """Test style checking."""
        from agents.linter.tools import check_style

        result = check_style(sample_code)

        assert isinstance(result, dict)
        assert "has_trailing_whitespace" in result

    def test_analyze_lint_result(self, temp_python_file):
        """Test lint result analysis."""
        from agents.linter.tools import lint_file, analyze_lint_result

        result = lint_file(temp_python_file)
        summary = analyze_lint_result(result)

        assert isinstance(summary, str)
        assert "issues" in summary.lower()