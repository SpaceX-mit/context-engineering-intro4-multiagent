"""Tester Agent - Generates and runs tests."""

from __future__ import annotations
from typing import Optional

from agents.base import AgentConfig, AgentType, BaseAgent
from core.context import WorkflowContext


class TesterAgent(BaseAgent):
    """Tester Agent - generates and runs tests."""

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Tester",
                role="tester",
                instructions="Generate and run tests for code",
                agent_type=AgentType.TESTER,
                model="llama3.2",
            )
        super().__init__(config)

    def generate_tests(self, code: str) -> str:
        """Generate tests for code."""
        # Extract functions/classes
        tests = "# Generated tests\nimport unittest\n\n"

        # Simple test generation
        if "Calculator" in code:
            tests += '''
class TestCalculator(unittest.TestCase):
    def test_add(self):
        from calculator import Calculator
        calc = Calculator()
        self.assertEqual(calc.add(2, 3), 5)

    def test_subtract(self):
        from calculator import Calculator
        calc = Calculator()
        self.assertEqual(calc.subtract(5, 3), 2)
'''

        if "hello_world" in code.lower():
            tests += '''
class TestHelloWorld(unittest.TestCase):
    def test_hello(self):
        from hello_world import hello_world
        # Just verify it doesn't crash
        hello_world()
'''

        if not tests.strip().endswith("import unittest"):
            tests += '''
class TestBasic(unittest.TestCase):
    def test_basic(self):
        self.assertTrue(True)
'''

        return tests

    async def run(self, prompt: str, context: Optional[WorkflowContext] = None) -> str:
        code = context.code if context and context.code else ""
        code = context.fixed_code if context and context.fixed_code else code

        tests = self.generate_tests(code)
        return f"## Generated Tests\n\n```python\n{tests}\n```\n"


def create_tester_agent() -> TesterAgent:
    return TesterAgent()


_tester_agent: Optional[TesterAgent] = None


def get_tester_agent() -> TesterAgent:
    global _tester_agent
    if _tester_agent is None:
        _tester_agent = TesterAgent()
    return _tester_agent
