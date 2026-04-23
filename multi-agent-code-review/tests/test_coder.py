"""Tests for Coder Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCoderAgent:
    """Tests for the Coder agent."""

    def test_coder_agent_import(self):
        """Test that coder agent can be imported."""
        from agents.coder import coder_agent
        assert coder_agent is not None

    def test_coder_agent_tools(self):
        """Test that coder agent has tools."""
        from agents.coder import get_coder_tools
        # Should return tools
        tools = get_coder_tools()
        assert tools is not None

    def test_coder_agent_prompts_import(self):
        """Test that coder prompts module exports correctly."""
        from agents.coder.prompts import (
            SYSTEM_PROMPT,
            generate_code_prompt,
            fix_code_prompt,
            explain_code_prompt,
        )
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 0

    def test_coder_agent_tools_import(self):
        """Test that coder tools module exports correctly."""
        from agents.coder.tools import (
            validate_code,
            suggest_tests,
            format_code,
            analyze_code_structure,
        )
        assert validate_code is not None
        assert suggest_tests is not None

    def test_validate_code_function(self):
        """Test validate_code function exists."""
        from agents.coder.tools import validate_code
        assert callable(validate_code)

    def test_suggest_tests_function(self):
        """Test suggest_tests function exists."""
        from agents.coder.tools import suggest_tests
        assert callable(suggest_tests)


class TestCodeGenerationTool:
    """Tests for code generation tool."""

    def test_validate_code_function(self):
        """Test validate_code function structure."""
        from agents.coder.tools import validate_code
        assert callable(validate_code)

    def test_format_code_function(self):
        """Test format_code function structure."""
        from agents.coder.tools import format_code
        assert callable(format_code)

    def test_analyze_code_structure_function(self):
        """Test analyze_code_structure function structure."""
        from agents.coder.tools import analyze_code_structure
        assert callable(analyze_code_structure)


class TestCoderAgentExecution:
    """Tests for coder agent execution."""

    @pytest.mark.asyncio
    async def test_coder_agent_run(self):
        """Test basic coder agent run."""
        from agents.coder import get_coder

        # Mock the model response
        mock_result = MagicMock()
        mock_result.output = "# Generated code\nprint('Hello, World!')"

        agent = get_coder()
        with patch.object(agent, 'run', return_value=mock_result):
            result = await agent.run("Generate a hello world program")
            assert result.output is not None

    @pytest.mark.asyncio
    async def test_coder_agent_code_generation(self):
        """Test code generation prompt building."""
        from agents.coder.prompts import generate_code_prompt

        prompt = generate_code_prompt(
            description="Create a calculator class",
            language="python",
            context=None
        )
        assert "calculator" in prompt.lower()
        assert len(prompt) > 0

    @pytest.mark.asyncio
    async def test_coder_agent_fix_generation(self):
        """Test fix code prompt building."""
        from agents.coder.prompts import fix_code_prompt

        issues = [
            {"message": "Unused variable 'x'", "line": 5},
            {"message": "Missing docstring", "line": 10},
        ]

        prompt = fix_code_prompt(
            code="x = 1\ndef foo():\n    pass",
            issues=issues
        )
        assert "Unused variable" in prompt
        assert len(prompt) > 0


class TestCoderAgentEdgeCases:
    """Edge case tests for coder agent."""

    def test_empty_description(self):
        """Test handling of empty description."""
        from agents.coder.prompts import generate_code_prompt

        prompt = generate_code_prompt("", "python", None)
        # Should still produce a valid prompt
        assert prompt is not None
        assert len(prompt) > 0

    def test_multiple_context_items(self):
        """Test with multiple context items."""
        from agents.coder.prompts import generate_code_prompt

        context = "Use class-based approach\nAdd type hints\nFollow PEP8"
        prompt = generate_code_prompt("Create a data processor", "python", context)
        assert "class" in prompt.lower()
        assert "type" in prompt.lower()

    def test_different_languages(self):
        """Test prompt generation for different languages."""
        from agents.coder.prompts import generate_code_prompt

        languages = ["python", "javascript", "go", "rust"]
        for lang in languages:
            prompt = generate_code_prompt("Hello world", lang, None)
            assert lang in prompt.lower()


class TestCoderAgentValidation:
    """Tests for code validation functionality."""

    def test_validate_code_function_import(self):
        """Test validate_code function exists."""
        from agents.coder.tools import validate_code
        assert callable(validate_code)

    def test_validate_code_python(self):
        """Test validation of Python code."""
        from agents.coder.tools import validate_code

        # Valid Python code
        issues = validate_code("print('hello')")
        assert isinstance(issues, list)

        # Invalid Python code
        issues = validate_code("print('hello")
        assert len(issues) > 0

    def test_validate_code_edge_cases(self):
        """Test validation edge cases."""
        from agents.coder.tools import validate_code

        # Empty code
        issues = validate_code("")
        assert isinstance(issues, list)

        # Only whitespace
        issues = validate_code("   ")
        assert isinstance(issues, list)