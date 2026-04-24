"""Context Passing Validation Tests.

Tests that verify Context is correctly passed between agents
during workflow execution, as specified in PRD.md Section 4.
"""

import asyncio
import pytest
from core.context import WorkflowContext, CodeIssue, Severity
from core.orchestrator import WorkflowOrchestrator


# Test fixtures
@pytest.fixture
def orchestrator():
    """Create a fresh orchestrator for each test."""
    return WorkflowOrchestrator()


@pytest.fixture
def context():
    """Create a fresh context for each test."""
    return WorkflowContext()


# Phase 3: Context Passing Tests
class TestContextPassing:
    """Test Context passing between agents."""

    def test_planner_receives_requirement(self, orchestrator, context):
        """Test that Planner receives requirement from context."""
        # Set requirement in context
        context.set_requirement("Create a calculator class")

        # Verify context has requirement
        assert context.requirement == "Create a calculator class"
        assert context.current_step == "pending"

        # Verify planner step can access it
        async def planner_handler(ctx, step):
            assert ctx.requirement == "Create a calculator class"
            ctx.set_plan("Step 1: Define Calculator class")
            return {"plan_created": True}

        orchestrator.register_step_handler("planner", "plan", planner_handler)

        workflows = orchestrator.list_workflows()
        dev_workflow = next(w for w in workflows if w.name == "DevelopmentWorkflow")

        result = asyncio.run(orchestrator.execute_workflow(dev_workflow.id, context))

        assert result.status.value == "completed"
        assert context.plan is not None

    def test_coder_receives_plan(self, orchestrator, context):
        """Test that Coder receives plan from context."""
        context.set_requirement("Create a calculator")
        context.set_plan("Step 1: Define Calculator class")

        async def coder_handler(ctx, step):
            # Coder should receive plan from context
            assert ctx.plan is not None
            ctx.set_code("class Calculator: pass")
            return {"code_generated": True}

        orchestrator.register_step_handler("coder", "implement", coder_handler)

        workflows = orchestrator.list_workflows()
        dev_workflow = next(w for w in workflows if w.name == "DevelopmentWorkflow")

        result = asyncio.run(orchestrator.execute_workflow(dev_workflow.id, context))

        assert result.status.value == "completed"
        assert context.code is not None

    def test_linter_receives_code(self, orchestrator, context):
        """Test that Linter receives code from context."""
        context.set_code("def hello(): pass")

        async def linter_handler(ctx, step):
            # Linter should receive code from context
            assert ctx.code is not None
            ctx.add_lint_issues([CodeIssue(line=1, severity=Severity.LOW, issue_type="style", message="Missing docstring")])
            return {"linted": True}

        orchestrator.register_step_handler("linter", "lint", linter_handler)

        workflows = orchestrator.list_workflows()
        dev_workflow = next(w for w in workflows if w.name == "DevelopmentWorkflow")

        result = asyncio.run(orchestrator.execute_workflow(dev_workflow.id, context))

        assert len(context.lint_issues) > 0

    def test_context_preservation_across_steps(self, orchestrator, context):
        """Test that context is preserved throughout workflow."""
        # Set initial requirement
        context.set_requirement("Create a calculator")

        # Track data flow
        data_received = {}

        async def planner_handler(ctx, step):
            data_received["planner"] = ctx.requirement
            ctx.set_plan("Plan from planner")

        async def coder_handler(ctx, step):
            data_received["coder"] = ctx.plan
            ctx.set_code("Code from coder")

        async def linter_handler(ctx, step):
            data_received["linter"] = ctx.code
            ctx.add_lint_issues([])

        async def reviewer_handler(ctx, step):
            data_received["reviewer"] = ctx.code
            ctx.add_review_issues([])

        async def fixer_handler(ctx, step):
            data_received["fixer"] = ctx.lint_issues + ctx.review_issues
            ctx.set_fixed_code("Fixed code")

        async def tester_handler(ctx, step):
            data_received["tester"] = ctx.fixed_code
            ctx.set_tests("Tests")

        orchestrator.register_step_handler("planner", "plan", planner_handler)
        orchestrator.register_step_handler("coder", "implement", coder_handler)
        orchestrator.register_step_handler("linter", "lint", linter_handler)
        orchestrator.register_step_handler("reviewer", "review", reviewer_handler)
        orchestrator.register_step_handler("fixer", "fix", fixer_handler)
        orchestrator.register_step_handler("tester", "test", tester_handler)

        workflows = orchestrator.list_workflows()
        dev_workflow = next(w for w in workflows if w.name == "DevelopmentWorkflow")

        result = asyncio.run(orchestrator.execute_workflow(dev_workflow.id, context))

        # Verify all agents received correct data
        assert data_received["planner"] == "Create a calculator"
        assert data_received["coder"] == "Plan from planner"
        assert data_received["linter"] == "Code from coder"
        assert data_received["reviewer"] == "Code from coder"
        assert isinstance(data_received["fixer"], list)
        assert data_received["tester"] == "Fixed code"


class TestWorkflowContext:
    """Test WorkflowContext data model."""

    def test_workflow_context_creation(self):
        """Test creating WorkflowContext."""
        ctx = WorkflowContext()
        assert ctx.requirement == ""
        assert ctx.plan is None
        assert ctx.code is None
        assert ctx.current_step == "pending"
        assert ctx.iteration == 0

    def test_context_setters(self):
        """Test context setter methods."""
        ctx = WorkflowContext()

        ctx.set_requirement("Test requirement")
        assert ctx.requirement == "Test requirement"

        ctx.set_plan("Test plan")
        assert ctx.plan == "Test plan"
        assert ctx.current_step == "planner_completed"

        ctx.set_code("Test code")
        assert ctx.code == "Test code"
        assert ctx.current_step == "coder_completed"

    def test_add_issues(self):
        """Test adding issues to context."""
        ctx = WorkflowContext()

        issues = [
            CodeIssue(line=1, severity=Severity.LOW, issue_type="style", message="Test"),
            CodeIssue(line=2, severity=Severity.HIGH, issue_type="logic", message="Test"),
        ]

        ctx.add_lint_issues(issues[:1])
        assert len(ctx.lint_issues) == 1
        assert ctx.current_step == "linter_completed"

        ctx.add_review_issues(issues[1:])
        assert len(ctx.review_issues) == 1
        assert ctx.current_step == "reviewer_completed"

    def test_get_critical_issues(self):
        """Test getting critical issues."""
        ctx = WorkflowContext()

        ctx.add_lint_issues([
            CodeIssue(severity=Severity.CRITICAL, issue_type="error", message="Critical"),
            CodeIssue(severity=Severity.LOW, issue_type="style", message="Low"),
        ])
        ctx.add_review_issues([
            CodeIssue(severity=Severity.HIGH, issue_type="logic", message="High"),
        ])

        critical = ctx.get_critical_issues()
        assert len(critical) == 1
        assert critical[0].severity == Severity.CRITICAL

    def test_is_quality_acceptable(self):
        """Test quality acceptance check."""
        ctx = WorkflowContext()

        # No critical issues = acceptable
        ctx.add_lint_issues([CodeIssue(severity=Severity.LOW)])
        assert ctx.is_quality_acceptable() is True

        # Critical issue = not acceptable
        ctx.add_review_issues([CodeIssue(severity=Severity.CRITICAL)])
        assert ctx.is_quality_acceptable() is False

    def test_to_dict(self):
        """Test context serialization."""
        ctx = WorkflowContext()
        ctx.set_requirement("Test")
        ctx.set_plan("Plan")

        d = ctx.to_dict()
        assert d["requirement"] == "Test"
        assert d["plan"] == "Plan"
        assert d["current_step"] == "planner_completed"


class TestEndToEnd:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_full_development_workflow(self):
        """Test complete development workflow."""
        orch = WorkflowOrchestrator()
        ctx = WorkflowContext()
        ctx.set_requirement("Create a hello world function")

        # Register simple handlers
        async def planner_handler(c, s):
            c.set_plan("1. Define function\n2. Add print")
            return {"planned": True}

        async def coder_handler(c, s):
            c.set_code('def hello_world():\n    print("Hello, World!")')
            return {"coded": True}

        async def linter_handler(c, s):
            c.add_lint_issues([])
            return {"linted": True}

        async def reviewer_handler(c, s):
            c.add_review_issues([])
            return {"reviewed": True}

        async def fixer_handler(c, s):
            c.set_fixed_code(c.code)
            return {"fixed": True}

        async def tester_handler(c, s):
            c.set_tests("def test_hello(): pass")
            return {"tested": True}

        orch.register_step_handler("planner", "plan", planner_handler)
        orch.register_step_handler("coder", "implement", coder_handler)
        orch.register_step_handler("linter", "lint", linter_handler)
        orch.register_step_handler("reviewer", "review", reviewer_handler)
        orch.register_step_handler("fixer", "fix", fixer_handler)
        orch.register_step_handler("tester", "test", tester_handler)

        workflows = orch.list_workflows()
        dev_workflow = next(w for w in workflows if w.name == "DevelopmentWorkflow")

        result = await orch.execute_workflow(dev_workflow.id, ctx)

        # Verify complete workflow
        assert result.status.value == "completed"
        assert result.steps_completed == 7
        assert ctx.code is not None
        assert ctx.tests is not None
