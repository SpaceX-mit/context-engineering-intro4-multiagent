"""Tests for workflow orchestration."""

import pytest

from core.workflow import WorkflowType


class TestWorkflow:
    """Test workflow execution."""

    def test_sequential_workflow(self, temp_python_file):
        """Test sequential workflow."""
        import asyncio

        from core.workflow import sequential_review_workflow

        result = asyncio.run(sequential_review_workflow(temp_python_file))

        assert result.files_reviewed == 1
        assert isinstance(result.summary.total_issues, int)

    def test_concurrent_workflow(self, temp_python_file):
        """Test concurrent workflow."""
        import asyncio

        from core.workflow import concurrent_review_workflow

        result = asyncio.run(concurrent_review_workflow(temp_python_file))

        assert result.files_reviewed == 1
        assert isinstance(result.summary.total_issues, int)

    def test_iterative_workflow(self, temp_python_file):
        """Test iterative workflow."""
        import asyncio

        from core.workflow import iterative_review_workflow

        result = asyncio.run(iterative_review_workflow(temp_python_file, max_iterations=2))

        assert result.files_reviewed == 1
        assert result.summary.total_issues >= 0

    def test_batch_review(self, temp_dir):
        """Test batch review of multiple files."""
        import asyncio

        from core.workflow import batch_review_workflow

        temp_dir, files = temp_dir
        results = asyncio.run(
            batch_review_workflow(files, parallel=False)
        )

        assert len(results) == len(files)


class TestWorkflowBuilder:
    """Test workflow builder."""

    def test_builder_add_agent(self):
        """Test adding agents to builder."""
        from core.workflow import WorkflowBuilder

        builder = WorkflowBuilder().add_agent("linter").add_agent("reviewer")
        config = builder.build()

        assert "linter" in config["agents"]
        assert "reviewer" in config["agents"]

    def test_builder_sequential(self):
        """Test sequential workflow setting."""
        from core.workflow import WorkflowBuilder

        builder = WorkflowBuilder().with_sequential()
        config = builder.build()

        assert config["workflow_type"] == WorkflowType.SEQUENTIAL

    def test_builder_iterative(self):
        """Test iterative workflow setting."""
        from core.workflow import WorkflowBuilder

        builder = WorkflowBuilder().with_iterative(max_iterations=5)
        config = builder.build()

        assert config["workflow_type"] == WorkflowType.ITERATIVE
        assert config["max_iterations"] == 5

    def test_builder_with_tests(self):
        """Test test inclusion setting."""
        from core.workflow import WorkflowBuilder

        builder = WorkflowBuilder().with_tests(False)
        config = builder.build()

        assert config["include_tests"] is False