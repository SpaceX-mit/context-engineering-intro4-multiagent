"""Tests for Reviewer Agent."""

import pytest

from core.models import Severity, IssueType


class TestReviewerTools:
    """Test reviewer tools."""

    def test_analyze_complexity(self, sample_code):
        """Test complexity analysis."""
        from agents.reviewer.tools import analyze_complexity

        result = analyze_complexity(sample_code)

        assert "file" in result
        assert "functions" in result
        assert "max_complexity" in result
        assert isinstance(result["functions"], list)

    def test_detect_security_issues(self, temp_python_file):
        """Test security issue detection."""
        from agents.reviewer.tools import detect_security_issues

        result = detect_security_issues(temp_python_file)

        assert result.agent == "reviewer"
        assert isinstance(result.issues, list)

    def test_assess_maintainability(self, sample_code):
        """Test maintainability assessment."""
        from agents.reviewer.tools import assess_maintainability

        result = assess_maintainability(sample_code)

        assert "score" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_review_file(self, temp_python_file):
        """Test full file review."""
        from agents.reviewer.tools import review_file

        result = review_file(temp_python_file)

        assert result.agent == "reviewer"
        assert result.status == "success"
        assert isinstance(result.issues, list)


class TestSecurityScanner:
    """Test security scanning."""

    def test_security_patterns(self):
        """Test detection of security patterns."""
        from tools.security_scanner import scan_security_issues

        # Code with potential SQL injection (using format)
        code = 'query = "SELECT * FROM users WHERE name = %s" % username\ncursor.execute(query)'
        issues = scan_security_issues(code)

        # Should detect SQL injection pattern
        assert any(i.rule_id == "B608" for i in issues) or len(issues) > 0

    def test_eval_detection(self):
        """Test eval usage detection."""
        from tools.security_scanner import scan_security_issues

        code = "result = eval(user_input)"
        issues = scan_security_issues(code)

        assert any(i.rule_id == "B102" for i in issues)

    def test_pickle_detection(self):
        """Test pickle usage detection."""
        from tools.security_scanner import scan_security_issues

        code = "data = pickle.load(file)"
        issues = scan_security_issues(code)

        assert any(i.rule_id == "B301" for i in issues)