"""AI Coder Agent System - Based on OpenAI Codex Architecture.

Multi-agent system with skills, session management, and context engineering.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from agent_framework import Agent, Message
from agent_framework.ollama import OllamaChatClient

from skills import Context, Skill, SkillResult, get_registry
from core.context import ContextManager
from core.session import Session, SessionManager


# ============================================================================
# Agent Types
# ============================================================================

class AgentType(Enum):
    COORDINATOR = "coordinator"
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    role: str
    instructions: str
    agent_type: AgentType
    model: str = "llama3.2"
    tools: List[str] = field(default_factory=list)
    enabled: bool = True


# ============================================================================
# Base Agent
# ============================================================================

class BaseAgent(ABC):
    """Base class for all AI Coder agents.

    Based on Codex agent architecture with:
    - Skill integration
    - Context management
    - Session awareness
    """

    def __init__(
        self,
        config: AgentConfig,
        client: OllamaChatClient,
        skills: Optional[List[Skill]] = None,
    ):
        self.config = config
        self.client = client
        self.skills = skills or []
        self._skill_registry = get_registry()

        # Create the underlying agent
        self._agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Create the agent_framework Agent."""
        skill_tools = [self._skill_registry.get(t) for t in self.config.tools if self._skill_registry.get(t)]

        # Filter out None skills
        active_tools = [t for t in skill_tools if t is not None]

        return Agent(
            client=self.client,
            name=self.config.name,
            instructions=self.config.instructions,
            tools=active_tools if active_tools else None,
        )

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> str:
        return self.config.role

    async def run(self, prompt: str, context: Optional[Context] = None) -> str:
        """Run the agent with a prompt."""
        result = await self._agent.run(prompt)
        return result.text if hasattr(result, "text") else str(result)

    async def run_streaming(self, prompt: str):
        """Run with streaming output."""
        async for chunk in self._agent.run(prompt, stream=True):
            if chunk.text:
                yield chunk.text

    async def execute_skill(self, skill_name: str, context: Context, **kwargs) -> SkillResult:
        """Execute a skill by name."""
        skill = self._skill_registry.get(skill_name)
        if not skill:
            return SkillResult(success=False, error=f"Skill not found: {skill_name}")
        return await skill.execute_with_timeout(context, **kwargs)


# ============================================================================
# Coordinator Agent
# ============================================================================

COORDINATOR_INSTRUCTIONS = """You are the Coordinator Agent in the AI Coder team.

Your role is to:
1. Understand user requirements
2. Plan the approach
3. Coordinate with specialized agents (Planner, Coder, Reviewer, Tester)
4. Aggregate results and present to user

## Team Members
- Planner: Breaks down requirements into tasks
- Coder: Writes and executes code
- Reviewer: Checks code quality
- Tester: Generates and runs tests

## Workflow
1. Parse the user's request
2. Route to appropriate agent(s)
3. Collect results
4. Present final response

## Output Format
Always structure your response:
1. **Understanding**: What you understood from the request
2. **Plan**: Steps you'll take
3. **Results**: What was done
4. **Output**: The final result/artifacts
"""


# ============================================================================
# Planner Agent
# ============================================================================

PLANNER_INSTRUCTIONS = """You are the Planner Agent in the AI Coder team.

Your role is to break down user requirements into clear implementation steps.

## When Given a Requirement:
1. Understand the goal
2. Identify necessary files and components
3. Create a step-by-step plan
4. Consider dependencies and order

## Output Format
Always respond with:
## Plan
1. [Step description]
2. [Step description]
...

### Files to Create/Modify
- [filename1]
- [filename2]

### Dependencies
- [Any external dependencies]

Be concise and practical."""


# ============================================================================
# Coder Agent
# ============================================================================

CODER_INSTRUCTIONS = """You are the Coder Agent in the AI Coder team.

Your role is to write clean, working Python code.

## When Given a Task:
1. Write complete, runnable code
2. Follow best practices (type hints, docstrings, error handling)
3. Execute code to verify it works
4. Present the code and results

## Skills Available
- shell: Execute shell commands
- code_runner: Execute Python code
- file_search: Search files
- linter: Run code linters

## Output Format
Always include:
### Code
```python
[Your code here]
```

### Execution Result
[Output from running the code]

Be concise and practical."""


# ============================================================================
# Reviewer Agent
# ============================================================================

REVIEWER_INSTRUCTIONS = """You are the Reviewer Agent in the AI Coder team.

Your role is to check code for issues and suggest improvements.

## When Given Code to Review:
1. Check for logic errors
2. Check for security issues
3. Check for code style
4. Check for edge cases

## Output Format
Always respond with:
## Review
### Issues Found
- [Issue 1] (severity: high/medium/low)
- [Issue 2]

### Suggestions
- [Suggestion 1]
...

### Overall Assessment
[Good/Poor] - [Brief summary]

If no issues, say "Code looks good!"

Be thorough but concise."""


# ============================================================================
# Tester Agent
# ============================================================================

TESTER_INSTRUCTIONS = """You are the Tester Agent in the AI Coder team.

Your role is to generate and run tests for code.

## When Given Code to Test:
1. Understand what the code does
2. Write tests for basic functionality
3. Write tests for edge cases
4. Run the tests

## Output Format
Always include:
### Tests
```python
[Your test code]
```

### Test Results
[Pass/Fail summary]

Be thorough."""


# ============================================================================
# Agent Factory
# ============================================================================

AGENT_CONFIGS = {
    AgentType.COORDINATOR: AgentConfig(
        name="Coordinator",
        role="Task coordinator and aggregator",
        instructions=COORDINATOR_INSTRUCTIONS,
        agent_type=AgentType.COORDINATOR,
    ),
    AgentType.PLANNER: AgentConfig(
        name="Planner",
        role="Task planner",
        instructions=PLANNER_INSTRUCTIONS,
        agent_type=AgentType.PLANNER,
        tools=["file_search"],
    ),
    AgentType.CODER: AgentConfig(
        name="Coder",
        role="Code writer and executor",
        instructions=CODER_INSTRUCTIONS,
        agent_type=AgentType.CODER,
        tools=["code_runner", "shell", "file_search"],
    ),
    AgentType.REVIEWER: AgentConfig(
        name="Reviewer",
        role="Code quality reviewer",
        instructions=REVIEWER_INSTRUCTIONS,
        agent_type=AgentType.REVIEWER,
        tools=["linter"],
    ),
    AgentType.TESTER: AgentConfig(
        name="Tester",
        role="Test generator",
        instructions=TESTER_INSTRUCTIONS,
        agent_type=AgentType.TESTER,
        tools=["code_runner", "shell"],
    ),
}


def create_agent(
    agent_type: AgentType,
    client: Optional[OllamaChatClient] = None,
    model: str = "llama3.2",
) -> BaseAgent:
    """Create an agent by type."""
    config = AGENT_CONFIGS[agent_type]
    if client is None:
        client = OllamaChatClient(model=model)

    if agent_type == AgentType.COORDINATOR:
        return CoordinatorAgent(config, client)
    elif agent_type == AgentType.PLANNER:
        return PlannerAgent(config, client)
    elif agent_type == AgentType.CODER:
        return CoderAgent(config, client)
    elif agent_type == AgentType.REVIEWER:
        return ReviewerAgent(config, client)
    elif agent_type == AgentType.TESTER:
        return TesterAgent(config, client)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


# ============================================================================
# Specialized Agents
# ============================================================================

class CoordinatorAgent(BaseAgent):
    """Coordinator agent for task orchestration."""

    async def run(self, prompt: str, context: Optional[Context] = None) -> str:
        """Run coordinator - parse request and delegate."""
        return await super().run(prompt, context)


class PlannerAgent(BaseAgent):
    """Planner agent for task breakdown."""

    async def plan(self, requirement: str) -> str:
        """Create a plan for the requirement."""
        return await self.run(f"Plan the implementation for: {requirement}")


class CoderAgent(BaseAgent):
    """Coder agent for code generation and execution."""

    async def write_code(self, spec: str) -> tuple[str, Optional[str]]:
        """Write code based on spec. Returns (code, output)."""
        response = await self.run(f"Write Python code for: {spec}")
        # Extract code from response
        code_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
        code = code_match.group(1).strip() if code_match else ""
        return code, response


class ReviewerAgent(BaseAgent):
    """Reviewer agent for code quality."""

    async def review(self, code: str) -> str:
        """Review the code."""
        return await self.run(f"Review this code:\n{code}")


class TesterAgent(BaseAgent):
    """Tester agent for test generation."""

    async def test(self, code: str) -> tuple[str, bool]:
        """Generate and run tests. Returns (test_code, passed)."""
        response = await self.run(f"Generate tests for:\n{code}")
        test_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
        test_code = test_match.group(1).strip() if test_match else ""
        return test_code, True  # Would execute tests here


# ============================================================================
# Multi-Agent Workflow
# ============================================================================

class AICoderWorkflow:
    """Workflow orchestrating multiple agents.

    Based on Codex multi-agent patterns.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        workspace_path: str = ".",
    ):
        self.model = model
        self.workspace_path = workspace_path

        # Create client
        self.client = OllamaChatClient(model=model)

        # Create context manager
        self.context_manager = ContextManager()

        # Create session manager
        self.session_manager = SessionManager()

        # Create agents
        self.coordinator = create_agent(AgentType.COORDINATOR, self.client, model)
        self.planner = create_agent(AgentType.PLANNER, self.client, model)
        self.coder = create_agent(AgentType.CODER, self.client, model)
        self.reviewer = create_agent(AgentType.REVIEWER, self.client, model)
        self.tester = create_agent(AgentType.TESTER, self.client, model)

        # Create session
        self.session = self.session_manager.create_session(
            model=model,
            workspace_path=workspace_path,
        )

    async def run(self, requirement: str) -> str:
        """Run the full workflow for a requirement."""
        # Add user message
        self.session.add_user_message(requirement)

        # Build context
        skills = get_registry().list_skills()
        system_prompt = self.context_manager.build_system_prompt(
            agent_name="AICoder",
            agent_role="Multi-agent code development system",
            skills=skills,
        )

        # Run through agents
        response_parts = []

        # 1. Coordinator parses request
        coord_response = await self.coordinator.run(
            f"Parse and plan: {requirement}"
        )
        response_parts.append(f"**Coordinator**: {coord_response}")

        # 2. Planner creates plan
        plan_response = await self.planner.plan(requirement)
        response_parts.append(f"\n**Planner**: {plan_response}")

        # 3. Coder writes code
        code, code_response = await self.coder.write_code(requirement)
        if code:
            self.session.add_artifact("generated_code.py", "code", code)
        response_parts.append(f"\n**Coder**: {code_response}")

        # 4. Reviewer reviews if code exists
        if code:
            review_response = await self.reviewer.review(code)
            response_parts.append(f"\n**Reviewer**: {review_response}")

        # Add assistant response
        full_response = "\n".join(response_parts)
        self.session.add_assistant_message(full_response)

        # Check if compaction needed
        if self.context_manager.should_compact():
            self.session.compact()

        return full_response

    async def run_streaming(self, requirement: str):
        """Run with streaming output."""
        # Add user message
        self.session.add_user_message(requirement)

        # Stream through coordinator
        async for chunk in self.coordinator.run_streaming(requirement):
            yield chunk


# ============================================================================
# Simple API
# ============================================================================

_workflow: Optional[AICoderWorkflow] = None


def get_aicoder_workflow(model: str = "llama3.2", workspace_path: str = ".") -> AICoderWorkflow:
    """Get or create the workflow singleton."""
    global _workflow
    if _workflow is None:
        _workflow = AICoderWorkflow(model=model, workspace_path=workspace_path)
    return _workflow


async def run_aicoder(requirement: str, model: str = "llama3.2") -> str:
    """Simple API to run aicoder."""
    workflow = get_aicoder_workflow(model=model)
    return await workflow.run(requirement)
