"""AI Coder Agent - Built with Microsoft Agent Framework.

Multi-agent system using:
- agent_framework.Agent for individual agents
- agent_framework.orchestrations.SequentialBuilder for workflow
- Ollama models with function calling support
"""

from __future__ import annotations

import asyncio
import io
import re
import sys
import time
from typing import Annotated, Dict, List, Optional, cast

from agent_framework import Agent, Message, tool
from agent_framework.ollama import OllamaChatClient
from agent_framework.orchestrations import SequentialBuilder
from pydantic import Field


# Default model
DEFAULT_MODEL = "llama3.2"


def get_ollama_client(model: str = DEFAULT_MODEL) -> OllamaChatClient:
    """Create Ollama chat client."""
    return OllamaChatClient(model=model)


# ============================================================================
# TOOLS
# ============================================================================

@tool(approval_mode="never_require")
def execute_python_code(
    code: Annotated[str, Field(description="Python code to execute")]
) -> str:
    """Execute Python code and return output."""
    start = time.time()
    stdout_c = io.StringIO()
    stderr_c = io.StringIO()

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stdout_c
    sys.stderr = stderr_c

    result = {"success": True, "output": "", "error": None}

    try:
        namespace = {
            "__name__": "__aicoder__",
            "__builtins__": {
                "print": print, "len": len, "range": range, "str": str,
                "int": int, "float": float, "list": list, "dict": dict,
                "set": set, "tuple": tuple, "bool": bool,
                "True": True, "False": False, "None": None,
                "enumerate": enumerate, "zip": zip, "sorted": sorted,
                "sum": sum, "min": min, "max": max, "abs": abs,
                "isinstance": isinstance, "type": type, "open": open,
                "input": input, "round": round, "pow": pow,
                "divmod": divmod, "any": any, "all": all,
            },
        }
        exec(code, namespace)
        result["output"] = stdout_c.getvalue()
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    exec_time = time.time() - start

    if result["success"]:
        return f"Output:\n{result['output'] or '(No output)'}\nExecution time: {exec_time:.3f}s"
    else:
        return f"Error: {result['error']}"


@tool(approval_mode="never_require")
def extract_code(
    text: Annotated[str, Field(description="Text containing code blocks")]
) -> str:
    """Extract Python code from markdown."""
    pattern = r"```python\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return matches[0].strip()
    pattern = r"```\n?(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[0].strip() if matches else ""


# ============================================================================
# AGENTS
# ============================================================================

def create_planner_agent(client: OllamaChatClient) -> Agent:
    """Planner agent - creates implementation plan."""
    return Agent(
        client=client,
        name="Planner",
        instructions="""You are a Planner agent. Your job is to break down user requirements into clear steps.

When given a requirement:
1. Understand what needs to be built
2. Create a step-by-step plan
3. List files to create

Be concise. Format as:
## Plan
1. [Step 1]
2. [Step 2]
...

### Files
- [file1]
- [file2]""",
    )


def create_coder_agent(client: OllamaChatClient) -> Agent:
    """Coder agent - writes Python code."""
    return Agent(
        client=client,
        name="Coder",
        instructions="""You are a Coder agent. Write clean, working Python code.

When given a spec:
1. Write complete, runnable Python code
2. Use markdown blocks: ```python ... ```
3. Always run code using execute_python_code tool

Keep code clean with basic error handling.""",
        tools=[execute_python_code],
    )


def create_reviewer_agent(client: OllamaChatClient) -> Agent:
    """Reviewer agent - checks code quality."""
    return Agent(
        client=client,
        name="Reviewer",
        instructions="""You are a Reviewer agent. Check code for issues.

Check for:
- Logic errors
- Security issues
- Code style

Format:
## Review
### Issues
- [Issue]
...
### Suggestions
- [Suggestion]
...

Or "Code looks good!" if no issues.""",
    )


# ============================================================================
# WORKFLOW
# ============================================================================

def create_aicoder_workflow(
    model: str = DEFAULT_MODEL,
    client: OllamaChatClient = None,
) -> SequentialBuilder:
    """Create multi-agent workflow: Planner -> Coder -> Reviewer."""
    if client is None:
        client = get_ollama_client(model)

    planner = create_planner_agent(client)
    coder = create_coder_agent(client)
    reviewer = create_reviewer_agent(client)

    workflow = SequentialBuilder(
        participants=[planner, coder, reviewer],
    ).build()

    return workflow


async def run_aicoder_workflow(
    requirement: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Run the full workflow and return combined response."""
    workflow = create_aicoder_workflow(model)

    outputs: List[List[Message]] = []
    async for event in workflow.run(requirement, stream=True):
        if event.type == "output":
            outputs.append(cast(List[Message], event.data))

    if not outputs:
        return "No output"

    # Combine all messages
    response = []
    for msg in outputs[-1]:
        if hasattr(msg, "text") and msg.text:
            response.append(f"**{msg.author_name or msg.role}:**\n{msg.text}")

    return "\n\n".join(response)


# ============================================================================
# SIMPLE AGENT (single agent with tools)
# ============================================================================

_agent: Optional[Agent] = None


def create_aicoder_agent(model: str = DEFAULT_MODEL) -> Agent:
    """Create AI Coder agent with code execution."""
    client = get_ollama_client(model)
    return Agent(
        client=client,
        name="AICoder",
        instructions="""You are an expert AI Coder. Build working software.

When asked to code:
1. Write clean Python code in markdown blocks
2. Execute with execute_python_code tool
3. Show output

Be concise and practical.""",
        tools=[execute_python_code],
    )


def get_aicoder_agent(model: str = DEFAULT_MODEL) -> Agent:
    """Get or create agent (lazy singleton per model)."""
    global _agent
    if _agent is None:
        _agent = create_aicoder_agent(model)
    return _agent


async def run_aicoder(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Run the AI Coder agent."""
    agent = get_aicoder_agent(model)
    result = await agent.run(prompt)
    return result.text if hasattr(result, "text") else str(result)


async def run_aicoder_streaming(prompt: str, model: str = DEFAULT_MODEL):
    """Run with streaming."""
    agent = get_aicoder_agent(model)
    async for chunk in agent.run(prompt, stream=True):
        if chunk.text:
            yield chunk.text
