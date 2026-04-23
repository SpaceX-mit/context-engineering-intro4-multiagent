"""Tests for Fixer Agent."""

import pytest

from core.models import Severity, IssueType


class TestFixerTools:
    """Test fixer tools."""

    def test_fix_imports(self, sample_code):
        """Test unused import removal."""
        from agents.fixer.tools import fix_imports

        fixed, issues_fixed = fix_imports(sample_code)

        assert isinstance(fixed, str)
        assert isinstance(issues_fixed, list)
        # Should have removed unused imports
        assert "import os" not in fixed or len(issues_fixed) > 0

    def test_verify_fix_valid(self):
        """Test fix verification for valid code."""
        from agents.fixer.tools import verify_fix

        original = "def hello():\n    return 'hello'\n"
        fixed = "def hello():\n    return 'hello'\n"

        result = verify_fix(original, fixed)

        assert result["valid"] is True
        assert result["syntax_ok"] is True
        assert result["changes"] == 0

    def test_verify_fix_changed(self):
        """Test fix verification for changed code."""
        from agents.fixer.tools import verify_fix

        original = "def hello():\n    return 'hello'\n"
        fixed = "def hello():\n    return 'Hello!'\n"

        result = verify_fix(original, fixed)

        assert result["valid"] is True
        assert result["syntax_ok"] is True
        assert result["changes"] == 1

    def test_verify_fix_invalid(self):
        """Test fix verification for invalid code."""
        from agents.fixer.tools import verify_fix

        original = "def hello():\n    return 'hello'\n"
        fixed = "def hello():\n    return 'hello'\n    }"

        result = verify_fix(original, fixed)

        assert result["valid"] is False
        assert result["syntax_ok"] is False

    def test_apply_fixes(self, temp_python_file):
        """Test applying fixes to a file."""
        from agents.fixer.tools import apply_fixes

        result = apply_fixes(temp_python_file, [])

        assert result.agent == "fixer"
        assert result.status == "success"


class TestCodeModification:
    """Test code modification utilities."""

    def test_split_long_line(self):
        """Test long line splitting."""
        from agents.fixer.tools import split_long_line

        long_line = "x = " + ", ".join([f"'{i}'" for i in range(50)])
        result = split_long_line(long_line)

        assert isinstance(result, list)
        assert len(result) > 1

    def test_add_underscore_prefix(self):
        """Test adding underscore to unused variable."""
        from agents.fixer.tools import add_underscore_prefix

        line = "    x = 1"
        result = add_underscore_prefix(line)

        assert "_x = 1" in result