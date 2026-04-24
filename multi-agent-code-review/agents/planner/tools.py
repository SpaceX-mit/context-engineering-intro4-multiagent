"""Tools for the Planner Agent."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanStep:
    """A single step in a plan."""
    step_number: int
    name: str
    description: str
    complexity: int = 1  # 1-5
    estimated_lines: int = 0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ImplementationPlan:
    """Complete implementation plan."""
    requirement: str = ""
    overview: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    estimated_effort: str = ""
    estimated_lines: int = 0


def create_plan(requirement: str) -> ImplementationPlan:
    """
    Create an implementation plan from a requirement.

    Args:
        requirement: User requirement

    Returns:
        Structured implementation plan
    """
    # Simple keyword-based planning
    req_lower = requirement.lower()
    plan = ImplementationPlan(requirement=requirement)

    # Basic overview
    plan.overview = f"Implement: {requirement}"

    # Add steps based on keywords
    if "class" in req_lower or "function" in req_lower:
        plan.steps.append(PlanStep(
            step_number=1,
            name="Define structure",
            description="Define the class/function structure",
            complexity=1,
            estimated_lines=10,
        ))

    if any(kw in req_lower for kw in ["add", "calculate", "compute"]):
        plan.steps.append(PlanStep(
            step_number=2,
            name="Implement core logic",
            description="Implement core functionality",
            complexity=2,
            estimated_lines=20,
        ))

    if any(kw in req_lower for kw in ["error", "exception", "invalid"]):
        plan.steps.append(PlanStep(
            step_number=3,
            name="Add error handling",
            description="Add error handling and validation",
            complexity=2,
            estimated_lines=15,
        ))

    if "test" in req_lower:
        plan.steps.append(PlanStep(
            step_number=4,
            name="Add tests",
            description="Write unit tests",
            complexity=1,
            estimated_lines=30,
        ))

    # Default steps if none matched
    if not plan.steps:
        plan.steps.append(PlanStep(
            step_number=1,
            name="Implement",
            description=f"Implement: {requirement}",
            complexity=2,
            estimated_lines=50,
        ))

    # Estimate effort
    total_lines = sum(s.estimated_lines for s in plan.steps)
    plan.estimated_lines = total_lines
    plan.estimated_effort = f"{total_lines} lines of code, ~{len(plan.steps)} steps"

    # Suggested files
    if "class" in req_lower:
        plan.files = ["src/models.py", "tests/test_models.py"]
    else:
        plan.files = ["src/main.py", "tests/test_main.py"]

    return plan


def estimate_effort(plan: ImplementationPlan) -> Dict[str, Any]:
    """
    Estimate effort for a plan.

    Args:
        plan: Implementation plan

    Returns:
        Effort estimation
    """
    total_complexity = sum(s.complexity for s in plan.steps)
    avg_complexity = total_complexity / len(plan.steps) if plan.steps else 0

    return {
        "total_steps": len(plan.steps),
        "total_lines": plan.estimated_lines,
        "avg_complexity": round(avg_complexity, 1),
        "estimated_hours": total_complexity * 0.5,  # Rough estimate
        "risk_level": "high" if avg_complexity > 3 else "medium" if avg_complexity > 2 else "low",
    }
