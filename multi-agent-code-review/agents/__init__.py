"""Agent modules for multi-agent code review.

Note: Agents require LLM API configuration. Import specific agents as needed.
"""

# Import tools directly instead of agents to avoid LLM initialization at import time
from agents.linter.tools import lint_file
from agents.reviewer.tools import review_file, detect_security_issues
from agents.test_agent.tools import analyze_coverage, suggest_tests
from agents.fixer.tools import apply_fixes, fix_imports
from agents.coordinator.tools import orchestrate_review, generate_report

__all__ = [
    "lint_file",
    "review_file",
    "detect_security_issues",
    "analyze_coverage",
    "suggest_tests",
    "apply_fixes",
    "fix_imports",
    "orchestrate_review",
    "generate_report",
]