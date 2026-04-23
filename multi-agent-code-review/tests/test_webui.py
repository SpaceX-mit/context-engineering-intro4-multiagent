"""Tests for WebUI components."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestChatComponent:
    """Tests for chat component."""

    def test_add_message_function(self):
        """Test add_message function."""
        from webui.components.chat import add_message

        history = [("Hello", "Hi there")]
        new_message = "How are you?"
        response = "I'm fine, thanks!"

        result = add_message(new_message, history, response)
        assert result[0] == ""  # Empty message
        assert len(result[1]) == 2  # History updated

    def test_clear_chat_function(self):
        """Test clear_chat function."""
        from webui.components.chat import clear_chat

        result = clear_chat()
        assert result == []

    def test_chat_manager(self):
        """Test ChatManager class."""
        from webui.components.chat import ChatManager

        manager = ChatManager()
        assert manager.history == []
        assert manager.agent is None

    def test_chat_manager_set_agent(self):
        """Test ChatManager set_agent method."""
        from webui.components.chat import ChatManager

        manager = ChatManager()
        mock_agent = MagicMock()
        manager.set_agent(mock_agent)
        assert manager.agent == mock_agent

    def test_chat_manager_get_history(self):
        """Test ChatManager get_history method."""
        from webui.components.chat import ChatManager

        manager = ChatManager()
        manager.history = [("Q1", "A1")]
        assert manager.get_history() == [("Q1", "A1")]

    def test_chat_manager_clear_history(self):
        """Test ChatManager clear_history method."""
        from webui.components.chat import ChatManager

        manager = ChatManager()
        manager.history = [("Q1", "A1")]
        manager.clear_history()
        assert manager.history == []


class TestCodeEditorComponent:
    """Tests for code editor component."""

    def test_update_code_language_python(self):
        """Test language detection for Python."""
        from webui.components.code_editor import update_code_language

        assert update_code_language("test.py") == "python"
        assert update_code_language("script.PY") == "python"

    def test_update_code_language_javascript(self):
        """Test language detection for JavaScript."""
        from webui.components.code_editor import update_code_language

        assert update_code_language("app.js") == "javascript"
        assert update_code_language("module.JS") == "javascript"

    def test_update_code_language_typescript(self):
        """Test language detection for TypeScript."""
        from webui.components.code_editor import update_code_language

        assert update_code_language("app.ts") == "typescript"
        assert update_code_language("component.TS") == "typescript"

    def test_update_code_language_unknown(self):
        """Test language detection for unknown extension."""
        from webui.components.code_editor import update_code_language

        result = update_code_language("file.xyz")
        assert result == "text"

    def test_code_editor_manager(self):
        """Test CodeEditorManager class."""
        from webui.components.code_editor import CodeEditorManager

        manager = CodeEditorManager()
        assert manager.current_file is None
        assert manager.modified is False
        assert manager.files == {}

    def test_code_editor_manager_new_file(self):
        """Test CodeEditorManager new_file method."""
        from webui.components.code_editor import CodeEditorManager

        manager = CodeEditorManager()
        result = manager.new_file("test.py", "# test content")
        assert "test.py" in result
        assert manager.current_file == "test.py"

    def test_code_editor_manager_is_modified(self):
        """Test CodeEditorManager is_modified method."""
        from webui.components.code_editor import CodeEditorManager

        manager = CodeEditorManager()
        assert manager.is_modified() is False


class TestFileBrowserComponent:
    """Tests for file browser component."""

    def test_list_project_files_import(self):
        """Test list_project_files function exists."""
        from webui.components.file_browser import list_project_files

        assert callable(list_project_files)

    def test_list_project_files_function(self):
        """Test list_project_files basic functionality."""
        from webui.components.file_browser import list_project_files

        # Test with current directory
        files = list_project_files(".")
        assert isinstance(files, list)

    def test_list_project_files_with_extensions(self):
        """Test list_project_files with specific extensions."""
        from webui.components.file_browser import list_project_files

        files = list_project_files(".", extensions=[".py"])
        # All returned files should end with .py
        for f in files:
            assert f.endswith(".py") or not f  # or empty list

    def test_file_browser_manager(self):
        """Test FileBrowserManager class."""
        from webui.components.file_browser import FileBrowserManager

        manager = FileBrowserManager()
        assert manager.root_path == "."
        assert manager.selected_files == []

    def test_file_browser_manager_get_files(self):
        """Test FileBrowserManager get_files method."""
        from webui.components.file_browser import FileBrowserManager

        manager = FileBrowserManager(".")
        files = manager.get_files()
        assert isinstance(files, list)

    def test_get_file_tree(self):
        """Test get_file_tree function."""
        from webui.components.file_browser import get_file_tree

        tree = get_file_tree(".")
        assert isinstance(tree, dict)
        assert "name" in tree
        assert "type" in tree
        assert tree["type"] == "folder"


class TestReviewPanelComponent:
    """Tests for review panel component."""

    def test_format_issues_for_display_empty(self):
        """Test formatting empty issues list."""
        from webui.components.review_panel import format_issues_for_display

        result = format_issues_for_display([])
        assert result == []

    def test_format_issues_for_display_single(self):
        """Test formatting single issue."""
        from webui.components.review_panel import format_issues_for_display

        issues = [{
            "file": "test.py",
            "line": 10,
            "severity": "high",
            "type": "security",
            "message": "SQL injection risk"
        }]

        result = format_issues_for_display(issues)
        assert len(result) == 1
        assert result[0][0] == "test.py"
        assert result[0][2] == "high"

    def test_format_issues_for_display_multiple(self):
        """Test formatting multiple issues."""
        from webui.components.review_panel import format_issues_for_display

        issues = [
            {"file": "a.py", "line": 1, "severity": "high", "type": "sec", "message": "Issue 1"},
            {"file": "b.py", "line": 2, "severity": "low", "type": "style", "message": "Issue 2"},
        ]

        result = format_issues_for_display(issues)
        assert len(result) == 2

    def test_filter_issues_no_filter(self):
        """Test filtering with no filter."""
        from webui.components.review_panel import filter_issues

        issues = [{"severity": "high"}, {"severity": "low"}]
        result = filter_issues(issues, "All", "All")
        assert len(result) == 2

    def test_filter_issues_by_severity(self):
        """Test filtering by severity."""
        from webui.components.review_panel import filter_issues

        issues = [
            {"severity": "high", "type": "sec"},
            {"severity": "low", "type": "style"},
            {"severity": "critical", "type": "sec"}
        ]

        result = filter_issues(issues, "High", "All")
        assert len(result) == 1
        assert result[0]["severity"] == "high"

    def test_filter_issues_by_type(self):
        """Test filtering by type."""
        from webui.components.review_panel import filter_issues

        issues = [
            {"severity": "high", "type": "security"},
            {"severity": "low", "type": "style"},
        ]

        result = filter_issues(issues, "All", "Security")
        assert len(result) == 1

    def test_filter_issues_combined(self):
        """Test filtering by both severity and type."""
        from webui.components.review_panel import filter_issues

        issues = [
            {"severity": "high", "type": "security"},
            {"severity": "low", "type": "security"},
            {"severity": "high", "type": "style"},
        ]

        result = filter_issues(issues, "High", "Security")
        assert len(result) == 1

    def test_review_panel_manager(self):
        """Test ReviewPanelManager class."""
        from webui.components.review_panel import ReviewPanelManager

        manager = ReviewPanelManager()
        assert manager.issues == []
        assert manager.selected_issue is None

    def test_review_panel_manager_add_issues(self):
        """Test adding issues to manager."""
        from webui.components.review_panel import ReviewPanelManager

        manager = ReviewPanelManager()
        issues = [{"message": "Test issue"}]
        manager.add_issues(issues)
        assert len(manager.issues) == 1

    def test_review_panel_manager_clear_issues(self):
        """Test clearing issues."""
        from webui.components.review_panel import ReviewPanelManager

        manager = ReviewPanelManager()
        manager.issues = [{"message": "Test"}]
        manager.clear_issues()
        assert len(manager.issues) == 0

    def test_review_panel_manager_get_summary(self):
        """Test getting issue summary."""
        from webui.components.review_panel import ReviewPanelManager

        manager = ReviewPanelManager()
        manager.issues = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]

        summary = manager.get_summary()
        assert summary["total"] == 4
        assert summary["critical"] == 1
        assert summary["high"] == 1

    def test_review_panel_manager_export_report(self):
        """Test exporting report."""
        from webui.components.review_panel import ReviewPanelManager

        manager = ReviewPanelManager()
        manager.issues = [{"severity": "high", "message": "Test"}]

        report = manager.export_report()
        assert "timestamp" in report
        assert "summary" in report
        assert "issues" in report


class TestWebUIImports:
    """Tests for WebUI module imports."""

    def test_import_all_components(self):
        """Test importing all components from __init__."""
        from webui.components import (
            ChatManager,
            CodeEditorManager,
            FileBrowserManager,
            ReviewPanelManager,
            format_issues_for_display,
            filter_issues,
            list_project_files,
        )

        assert callable(format_issues_for_display)
        assert callable(filter_issues)
        assert callable(list_project_files)


class TestWebUIComponentIntegration:
    """Integration tests for WebUI components."""

    def test_component_chain_file_browser_to_editor(self):
        """Test file browser selection updates editor."""
        from webui.components.file_browser import FileBrowserManager
        from webui.components.code_editor import CodeEditorManager

        browser = FileBrowserManager(".")
        editor = CodeEditorManager()

        # Create a test file
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# test")
            temp_path = f.name

        try:
            content = browser.select_file(temp_path)
            assert content == "# test"
        finally:
            os.unlink(temp_path)

    def test_review_panel_with_issues(self):
        """Test review panel with issues flows."""
        from webui.components.review_panel import ReviewPanelManager

        manager = ReviewPanelManager()

        issues = [
            {"severity": "critical", "type": "security", "message": "SQL injection"},
            {"severity": "high", "type": "correctness", "message": "Null check missing"},
            {"severity": "medium", "type": "style", "message": "Line too long"},
        ]

        manager.add_issues(issues)

        # Test filtering
        filtered = manager.get_issues()
        assert len(filtered) == 3

        summary = manager.get_summary()
        assert summary["total"] == 3
        assert summary["critical"] == 1

        report = manager.export_report()
        assert "issues" in report