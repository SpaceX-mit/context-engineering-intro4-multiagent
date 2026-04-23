"""Tests for core models."""

import pytest

from core.models import (
    Severity,
    IssueType,
    CodeIssue,
    ReviewResult,
    ReviewReport,
    ReviewRequest,
    WorkflowState,
)


class TestModels:
    """Test data models."""

    def test_severity_enum(self):
        """Test Severity enum values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"

    def test_issue_type_enum(self):
        """Test IssueType enum values."""
        assert IssueType.LINT.value == "lint"
        assert IssueType.CORRECTNESS.value == "correctness"
        assert IssueType.SECURITY.value == "security"
        assert IssueType.COMPLEXITY.value == "complexity"
        assert IssueType.TEST.value == "test"

    def test_code_issue_creation(self):
        """Test CodeIssue creation."""
        issue = CodeIssue(
            file="test.py",
            line=10,
            severity=Severity.HIGH,
            issue_type=IssueType.LINT,
            message="Test issue",
            auto_fixable=True,
            rule_id="E501",
        )

        assert issue.file == "test.py"
        assert issue.line == 10
        assert issue.severity == Severity.HIGH
        assert issue.auto_fixable is True

    def test_code_issue_to_dict(self):
        """Test CodeIssue serialization."""
        issue = CodeIssue(
            file="test.py",
            line=10,
            severity=Severity.HIGH,
            issue_type=IssueType.LINT,
            message="Test issue",
        )

        data = issue.to_dict()

        assert data["file"] == "test.py"
        assert data["severity"] == "high"
        assert data["type"] == "lint"

    def test_review_result_creation(self):
        """Test ReviewResult creation."""
        result = ReviewResult(
            agent="linter",
            issues=[],
            summary="Test summary",
            status="success",
        )

        assert result.agent == "linter"
        assert result.status == "success"

    def test_review_report_from_results(self):
        """Test ReviewReport creation from results."""
        issue = CodeIssue(
            file="test.py",
            severity=Severity.HIGH,
            issue_type=IssueType.LINT,
            message="Test",
        )

        result = ReviewResult(
            agent="linter",
            issues=[issue],
            status="success",
        )

        report = ReviewReport.from_results([result], 1)

        assert report.files_reviewed == 1
        assert report.summary.total_issues == 1
        assert report.summary.high == 1

    def test_review_report_to_dict(self):
        """Test ReviewReport serialization."""
        report = ReviewReport(files_reviewed=1)

        data = report.to_dict()

        assert data["files_reviewed"] == 1
        assert "timestamp" in data
        assert "summary" in data

    def test_review_request_validation(self):
        """Test ReviewRequest validation."""
        request = ReviewRequest(
            paths=["file.py"],
            auto_fix=True,
            max_iterations=5,
        )

        assert len(request.paths) == 1
        assert request.max_iterations == 5

    def test_workflow_state(self):
        """Test WorkflowState."""
        state = WorkflowState()

        assert state.status == "running"
        assert state.is_complete() is False
        # No issues, so should not continue
        assert state.should_continue(3) is False

        # Add an issue
        state.issues.append(
            CodeIssue(
                file="test.py",
                severity=Severity.HIGH,
                issue_type=IssueType.LINT,
                message="Test issue",
            )
        )
        assert state.should_continue(3) is True

        state.status = "completed"
        assert state.is_complete() is True