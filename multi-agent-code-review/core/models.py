"""Core data models for code review."""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Severity(Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(Enum):
    """Type of code issue."""

    LINT = "lint"
    CORRECTNESS = "correctness"
    SECURITY = "security"
    COMPLEXITY = "complexity"
    TEST = "test"


class CodeIssue(BaseModel):
    """Single code issue."""

    file: str = Field(..., description="File path")
    line: Optional[int] = Field(None, description="Line number")
    column: Optional[int] = Field(None, description="Column number")
    severity: Severity
    issue_type: IssueType
    message: str = Field(..., description="Issue description")
    suggestion: Optional[str] = Field(None, description="Fix suggestion")
    auto_fixable: bool = Field(False, description="Can be auto-fixed")
    rule_id: Optional[str] = Field(None, description="Rule identifier")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity.value,
            "type": self.issue_type.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "auto_fixed": self.auto_fixable,
            "rule_id": self.rule_id,
        }


class ReviewResult(BaseModel):
    """Result from a single agent."""

    agent: str = Field(..., description="Agent name")
    issues: List[CodeIssue] = Field(default_factory=list)
    summary: str = Field("", description="Brief summary")
    status: Literal["success", "error", "pending"] = "pending"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent": self.agent,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "status": self.status,
        }


class ReviewSummary(BaseModel):
    """Summary statistics for review."""

    total_issues: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    auto_fixed: int = 0


class ReviewReport(BaseModel):
    """Final review report."""

    timestamp: datetime = Field(default_factory=datetime.now)
    files_reviewed: int = Field(0, ge=0)
    summary: ReviewSummary = Field(default_factory=ReviewSummary)
    details: List[CodeIssue] = Field(default_factory=list)
    agents_used: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "files_reviewed": self.files_reviewed,
            "summary": {
                "total_issues": self.summary.total_issues,
                "critical": self.summary.critical,
                "high": self.summary.high,
                "medium": self.summary.medium,
                "low": self.summary.low,
                "auto_fixed": self.summary.auto_fixed,
            },
            "details": [i.to_dict() for i in self.details],
            "agents_used": self.agents_used,
        }

    @classmethod
    def from_results(cls, results: List[ReviewResult], files_reviewed: int) -> "ReviewReport":
        """Create report from multiple review results."""
        summary = ReviewSummary()
        details: List[CodeIssue] = []
        agents_used = []

        for result in results:
            if result.status == "success":
                agents_used.append(result.agent)
                for issue in result.issues:
                    details.append(issue)
                    summary.total_issues += 1
                    if issue.severity == Severity.CRITICAL:
                        summary.critical += 1
                    elif issue.severity == Severity.HIGH:
                        summary.high += 1
                    elif issue.severity == Severity.MEDIUM:
                        summary.medium += 1
                    elif issue.severity == Severity.LOW:
                        summary.low += 1
                    if issue.auto_fixable and issue.suggestion:
                        summary.auto_fixed += 1

        return cls(
            files_reviewed=files_reviewed,
            summary=summary,
            details=details,
            agents_used=agents_used,
        )


class ReviewRequest(BaseModel):
    """User review request."""

    paths: List[str] = Field(..., description="Paths to review")
    include_security: bool = Field(True)
    include_complexity: bool = Field(True)
    auto_fix: bool = Field(True)
    max_iterations: int = Field(3, ge=1, le=10)


class WorkflowState(BaseModel):
    """State for workflow execution."""

    current_agent: str = ""
    issues: List[CodeIssue] = Field(default_factory=list)
    iterations: int = 0
    status: Literal["running", "completed", "failed"] = "running"

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return self.status in ("completed", "failed")

    def should_continue(self, max_iterations: int) -> bool:
        """Check if workflow should continue."""
        if self.status != "running":
            return False
        if self.iterations >= max_iterations:
            return False
        # Continue if there are issues
        return len(self.issues) > 0