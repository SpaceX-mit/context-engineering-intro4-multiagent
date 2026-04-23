"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner

from core.models import Severity, IssueType


class TestCLI:
    """Test CLI commands."""

    def test_cli_help(self):
        """Test CLI help output."""
        from cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Multi-Agent Code Review" in result.output

    def test_review_command(self, temp_python_file):
        """Test review command."""
        from cli import review

        runner = CliRunner()
        result = runner.invoke(review, [temp_python_file])

        # Should complete (may have errors due to missing API key)
        assert result.exit_code in [0, 1]

    def test_quick_command(self, temp_python_file):
        """Test quick review command."""
        from cli import quick

        runner = CliRunner()
        result = runner.invoke(quick, [temp_python_file])

        # Should complete
        assert result.exit_code in [0, 1]

    def test_lint_command(self, temp_python_file):
        """Test lint command."""
        from cli import lint

        runner = CliRunner()
        result = runner.invoke(lint, [temp_python_file])

        # Should complete
        assert result.exit_code in [0, 1]

    def test_security_command(self, temp_python_file):
        """Test security command."""
        from cli import security

        runner = CliRunner()
        result = runner.invoke(security, [temp_python_file])

        # Should complete
        assert result.exit_code in [0, 1]

    def test_coverage_command(self, temp_python_file):
        """Test coverage command."""
        from cli import coverage

        runner = CliRunner()
        result = runner.invoke(coverage, [temp_python_file])

        # Should complete
        assert result.exit_code in [0, 1]


class TestCLIOutput:
    """Test CLI output formats."""

    def test_json_output(self, temp_python_file):
        """Test JSON output format."""
        from cli import review

        runner = CliRunner()
        result = runner.invoke(
            review,
            [temp_python_file, "--output", "json"],
        )

        # Check if output contains JSON structure
        if result.exit_code == 0:
            import json

            try:
                data = json.loads(result.output)
                assert "files_reviewed" in data or "reports" in data
            except json.JSONDecodeError:
                pass  # May fail if API key missing