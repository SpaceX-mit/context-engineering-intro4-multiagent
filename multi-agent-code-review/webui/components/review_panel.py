"""Review panel component for Gradio interface."""

from typing import List, Tuple

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    gr = None
    GRADIO_AVAILABLE = False


def create_review_panel_component() -> Tuple:
    """
    Create the review panel component.

    Returns:
        Tuple of (issues_table, details_json, refresh_btn)
    """
    if gr is None:
        raise ImportError("Gradio is not installed. Run: pip install gradio")

    with gr.Column():
        gr.Markdown("### Code Review")

        issues_table = gr.Dataframe(
            headers=["File", "Line", "Severity", "Type", "Message"],
            label="Issues Found",
            interactive=False,
            height=200,
        )

        with gr.Row():
            filter_severity = gr.Dropdown(
                choices=["All", "Critical", "High", "Medium", "Low"],
                value="All",
                label="Filter by Severity",
                scale=2,
            )
            filter_type = gr.Dropdown(
                choices=["All", "Correctness", "Security", "Complexity", "Style"],
                value="All",
                label="Filter by Type",
                scale=2,
            )

        details_json = gr.JSON(
            label="Issue Details",
            height=150,
        )

        with gr.Row():
            fix_selected_btn = gr.Button("Fix Selected", variant="primary")
            fix_all_btn = gr.Button("Fix All", variant="primary")
            export_btn = gr.Button("Export Report")

    return (
        issues_table,
        filter_severity,
        filter_type,
        details_json,
        fix_selected_btn,
        fix_all_btn,
        export_btn,
    )


def format_issues_for_display(issues: List[dict]) -> List[List]:
    """
    Format issues for Dataframe display.

    Args:
        issues: List of issue dictionaries

    Returns:
        List of rows for Dataframe
    """
    rows = []
    for issue in issues:
        rows.append(
            [
                issue.get("file", ""),
                issue.get("line", ""),
                issue.get("severity", ""),
                issue.get("type", ""),
                issue.get("message", ""),
            ]
        )
    return rows


def filter_issues(
    issues: List[dict],
    severity: str = "All",
    issue_type: str = "All",
) -> List[dict]:
    """
    Filter issues by severity and type.

    Args:
        issues: List of issue dictionaries
        severity: Severity to filter by
        issue_type: Type to filter by

    Returns:
        Filtered list of issues
    """
    filtered = issues

    if severity != "All":
        severity_lower = severity.lower()
        filtered = [i for i in filtered if i.get("severity", "").lower() == severity_lower]

    if issue_type != "All":
        type_lower = issue_type.lower()
        filtered = [i for i in filtered if i.get("type", "").lower() == type_lower]

    return filtered


class ReviewPanelManager:
    """Manager for review panel operations."""

    def __init__(self):
        self.issues: List[dict] = []
        self.selected_issue: dict = None

    def add_issues(self, issues: List[dict]):
        """Add issues to the panel."""
        self.issues.extend(issues)

    def clear_issues(self):
        """Clear all issues."""
        self.issues = []
        self.selected_issue = None

    def get_issues(self) -> List[dict]:
        """Get all issues."""
        return self.issues

    def select_issue(self, index: int) -> dict:
        """Select an issue by index."""
        if 0 <= index < len(self.issues):
            self.selected_issue = self.issues[index]
        return self.selected_issue

    def get_summary(self) -> dict:
        """Get summary of issues by severity."""
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": len(self.issues)}

        for issue in self.issues:
            severity = issue.get("severity", "").lower()
            if severity in summary:
                summary[severity] += 1

        return summary

    def export_report(self) -> str:
        """Export issues as a report."""
        import json
        from datetime import datetime

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "issues": self.issues,
        }

        return json.dumps(report, indent=2)


# Global review panel manager
review_panel_manager = ReviewPanelManager()
