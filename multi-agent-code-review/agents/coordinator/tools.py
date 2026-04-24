"""Tools for the Coordinator Agent."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Task:
    """A task to be executed by an agent."""
    name: str
    agent: str
    action: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class RequirementAnalysis:
    """Analysis of a user requirement."""
    summary: str
    components: List[str]
    complexity: int  # 1-5
    workflow_type: str  # sequential/concurrent/iterative
    agent_sequence: List[str]
    tasks: List[Task] = field(default_factory=list)


def parse_requirement(requirement: str) -> RequirementAnalysis:
    """
    Parse a user requirement into structured components.

    Args:
        requirement: Raw user requirement

    Returns:
        Structured requirement analysis
    """
    # Simple keyword-based parsing
    requirement_lower = requirement.lower()

    # Determine complexity
    complexity = 1
    if any(kw in requirement_lower for kw in ["complex", "multiple", "several"]):
        complexity = 3
    if any(kw in requirement_lower for kw in ["simple", "basic", "hello"]):
        complexity = 1

    # Determine workflow type
    if any(kw in requirement_lower for kw in ["concurrent", "parallel", "multiple agents"]):
        workflow_type = "concurrent"
    elif any(kw in requirement_lower for kw in ["iterate", "improve", "refine"]):
        workflow_type = "iterative"
    else:
        workflow_type = "sequential"

    # Determine agent sequence
    if "review" in requirement_lower or "check" in requirement_lower:
        agent_sequence = ["linter", "reviewer"]
    elif "test" in requirement_lower:
        agent_sequence = ["coder", "tester"]
    else:
        agent_sequence = ["planner", "coder", "linter", "reviewer", "fixer", "tester"]

    return RequirementAnalysis(
        summary=requirement[:100] + "..." if len(requirement) > 100 else requirement,
        components=[requirement],
        complexity=complexity,
        workflow_type=workflow_type,
        agent_sequence=agent_sequence,
    )


def decompose_tasks(analysis: RequirementAnalysis) -> List[Task]:
    """
    Decompose requirement analysis into specific tasks.

    Args:
        analysis: Parsed requirement analysis

    Returns:
        List of tasks to execute
    """
    tasks = []

    # Planner task
    if "planner" in analysis.agent_sequence:
        tasks.append(Task(
            name="plan",
            agent="planner",
            action="plan",
            input_data={"requirement": analysis.summary},
        ))

    # Coder task
    if "coder" in analysis.agent_sequence:
        tasks.append(Task(
            name="implement",
            agent="coder",
            action="implement",
            input_data={},
        ))

    # Linter task
    if "linter" in analysis.agent_sequence:
        tasks.append(Task(
            name="lint",
            agent="linter",
            action="lint",
            input_data={},
        ))

    # Reviewer task
    if "reviewer" in analysis.agent_sequence:
        tasks.append(Task(
            name="review",
            agent="reviewer",
            action="review",
            input_data={},
        ))

    # Fixer task
    if "fixer" in analysis.agent_sequence:
        tasks.append(Task(
            name="fix",
            agent="fixer",
            action="fix",
            input_data={},
        ))

    # Tester task
    if "tester" in analysis.agent_sequence:
        tasks.append(Task(
            name="test",
            agent="tester",
            action="test",
            input_data={},
        ))

    return tasks


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate results from multiple agents.

    Args:
        results: List of results from agents

    Returns:
        Aggregated result summary
    """
    total_issues = 0
    critical_issues = 0
    fixed_issues = 0
    actions_taken = []

    for result in results:
        if "issues" in result:
            total_issues += len(result["issues"])
            critical_issues += len([i for i in result["issues"] if i.get("severity") == "critical"])

        if "fixed" in result:
            fixed_issues += result["fixed"]

        if "action" in result:
            actions_taken.append(result["action"])

    return {
        "summary": f"Processed {len(results)} agent results",
        "total_issues": total_issues,
        "critical_issues": critical_issues,
        "fixed_issues": fixed_issues,
        "actions_taken": actions_taken,
        "success": critical_issues == 0,
    }
