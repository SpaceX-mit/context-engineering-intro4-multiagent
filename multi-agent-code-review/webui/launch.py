"""Launch AI Coder Multi-Agent System - Unified Gradio Interface.

Shows detailed agent execution flow in chat with input/output for each agent.
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from core.context import WorkflowContext, CodeIssue, Severity
from core.orchestrator import WorkflowOrchestrator, StepInput

from agents.coordinator.agent import get_coordinator_agent
from agents.planner.agent import get_planner_agent
from agents.coder.agent import get_coder_agent
from agents.reviewer.agent import get_reviewer_agent
from agents.linter.agent import get_linter_agent
from agents.fixer.agent import get_fixer_agent
from agents.test_agent.agent import get_tester_agent


# Agent nicknames for display
AGENT_NAMES = {
    "coordinator": "🧠 Alex (Coordinator)",
    "planner": "📋 Sam (Planner)",
    "coder": "💻 Codey (Coder)",
    "linter": "📝 Lint (Linter)",
    "reviewer": "🔍 Robie (Reviewer)",
    "fixer": "🔧 Fix (Fixer)",
    "tester": "🧪 Testy (Tester)",
}


class WorkflowRunner:
    """Manages workflow execution with detailed step tracking."""

    def __init__(self):
        self.orch = WorkflowOrchestrator()
        self._setup_handlers()
        self.step_logs = []

    def _setup_handlers(self):
        """Set up workflow handlers with step tracking."""

        async def coordinator_handler(step_input, context):
            self.step_logs.append({
                "agent": "coordinator",
                "action": "analyze",
                "input": "User requirement",
                "output": "Task decomposed",
            })
            return "Task analyzed and decomposed"

        async def planner_handler(step_input, context):
            requirement = step_input.data
            if isinstance(requirement, dict):
                requirement = requirement.get("requirement", str(requirement))

            self.step_logs.append({
                "agent": "planner",
                "action": "plan",
                "input": f"Requirement: {requirement[:50]}...",
                "output": None,  # Will be updated
            })

            plan = get_planner_agent().plan(requirement)
            self.step_logs[-1]["output"] = f"Plan created with {len(plan.steps)} steps"
            return plan.overview

        async def coder_handler(step_input, context):
            plan_text = step_input.data
            if isinstance(plan_text, dict):
                plan_text = plan_text.get("plan", str(plan_text))

            self.step_logs.append({
                "agent": "coder",
                "action": "implement",
                "input": f"Plan: {plan_text[:50]}...",
                "output": None,
            })

            code = get_coder_agent().implement(context.requirement, plan=plan_text)
            self.step_logs[-1]["output"] = f"Generated {len(code.splitlines())} lines of code"
            return code

        async def linter_handler(step_input, context):
            code = step_input.data
            if isinstance(code, dict):
                code = code.get("code", str(code))

            self.step_logs.append({
                "agent": "linter",
                "action": "lint",
                "input": f"Code ({len(code.splitlines())} lines)",
                "output": None,
            })

            issues = get_linter_agent().lint(code)
            self.step_logs[-1]["output"] = f"Found {len(issues)} style issues"
            return issues

        async def reviewer_handler(step_input, context):
            code = step_input.data
            if isinstance(code, dict):
                code = code.get("code", str(code))

            self.step_logs.append({
                "agent": "reviewer",
                "action": "review",
                "input": f"Code ({len(code.splitlines())} lines)",
                "output": None,
            })

            result = get_reviewer_agent().review(code)
            self.step_logs[-1]["output"] = f"Quality score: {result.score}/100, {len(result.issues)} issues"
            return result.issues

        async def fixer_handler(step_input, context):
            data = step_input.data
            if isinstance(data, dict):
                code = data.get("code", "")
                all_issues = data.get("issues", [])
            else:
                code = context.code or ""
                all_issues = []

            self.step_logs.append({
                "agent": "fixer",
                "action": "fix",
                "input": f"Code + {len(all_issues)} issues",
                "output": None,
            })

            fixed = get_fixer_agent().fix(code, all_issues)
            self.step_logs[-1]["output"] = f"Applied {len(all_issues)} fixes"
            return fixed

        async def tester_handler(step_input, context):
            code = step_input.data
            if isinstance(code, dict):
                code = code.get("fixed_code", str(code))

            self.step_logs.append({
                "agent": "tester",
                "action": "test",
                "input": f"Fixed code ({len(code.splitlines())} lines)",
                "output": None,
            })

            tests = get_tester_agent().generate_tests(code)
            self.step_logs[-1]["output"] = f"Generated {len(tests.splitlines())} lines of tests"
            return tests

        # Register handlers
        self.orch.register_step_handler("coordinator", "analyze", coordinator_handler)
        self.orch.register_step_handler("planner", "plan", planner_handler)
        self.orch.register_step_handler("coder", "implement", coder_handler)
        self.orch.register_step_handler("linter", "lint", linter_handler)
        self.orch.register_step_handler("reviewer", "review", reviewer_handler)
        self.orch.register_step_handler("fixer", "fix", fixer_handler)
        self.orch.register_step_handler("tester", "test", tester_handler)

    def run(self, requirement: str) -> dict:
        """Run workflow and return results."""
        self.step_logs = []
        ctx = WorkflowContext()
        ctx.set_requirement(requirement)

        workflows = self.orch.list_workflows()
        dev_workflow = next(w for w in workflows if w.name == "DevelopmentWorkflow")

        result = asyncio.run(self.orch.execute_workflow(dev_workflow.id, ctx))

        return {
            "status": result.status.value,
            "context": ctx,
            "step_logs": self.step_logs,
            "errors": result.errors,
        }


# Global runner
runner = WorkflowRunner()


def format_step_log(log: dict) -> str:
    """Format a step log for chat display."""
    agent = log["agent"]
    agent_display = AGENT_NAMES.get(agent, agent.upper())
    action = log["action"]
    input_text = log["input"]
    output_text = log["output"]

    # Truncate long text
    if len(input_text) > 80:
        input_text = input_text[:77] + "..."
    if output_text and len(output_text) > 80:
        output_text = output_text[:77] + "..."

    return f"""**{agent_display}**
├─ Action: `{action}`
├─ 📥 Input: {input_text}
└─ 📤 Output: {output_text or '[Processing...]'}"""


def run_workflow_streaming(requirement: str):
    """Generator that yields step results for streaming display."""
    yield "🤔 Starting workflow analysis...\n\n"

    try:
        result = runner.run(requirement)

        # Format all step logs
        yield "## 🔄 Multi-Agent Workflow Execution\n\n"

        for i, log in enumerate(result["step_logs"], 1):
            formatted = format_step_log(log)
            yield f"### Step {i}\n{formatted}\n\n"
            yield f"---\n\n"

        # Final summary
        ctx = result["context"]

        yield f"""## ✅ Workflow Complete

**Status:** `{result['status'].upper()}`

### 📋 Summary

| Agent | Status |
|-------|--------|
"""
        for log in result["step_logs"]:
            agent = log["agent"]
            status = "✓ Done" if log["output"] else "○ Pending"
            yield f"| {AGENT_NAMES.get(agent, agent)} | {status} |\n"

        yield f"""

### 💻 Generated Code

```python
{ctx.code or 'No code generated'}
```

### 📊 Issues Found
- Lint issues: {len(ctx.lint_issues)}
- Review issues: {len(ctx.review_issues)}

### 🧪 Generated Tests

```python
{ctx.tests or 'No tests generated'}
```
"""

        if result["errors"]:
            yield f"\n⚠️ **Errors:** {result['errors']}\n"

    except Exception as e:
        yield f"❌ **Error:** {str(e)}\n"


def handle_chat(message: str, history: list) -> tuple:
    """Handle chat message with streaming response."""
    if not message.strip():
        return "", history

    # Add user message
    history.append([message, "🤖 Starting multi-agent workflow...\n\n*(Each agent's execution will be shown below)*"])

    try:
        # Collect all output
        full_response = ""
        for chunk in run_workflow_streaming(message):
            full_response += chunk

        history[-1] = [message, full_response]

    except Exception as e:
        history[-1] = [message, f"❌ Error: {str(e)}"]

    return "", history


# Create Gradio interface
with gr.Blocks(title="AI Coder - Multi-Agent System") as demo:
    gr.Markdown("""
    # 🧠 AI Coder - Multi-Agent Code Development System

    Describe what you want to build. Watch each agent execute in real-time!
    """)

    gr.Markdown("""
    ### Agent Pipeline
    🧠 Coordinator → 📋 Planner → 💻 Coder → 📝 Linter → 🔍 Reviewer → 🔧 Fixer → 🧪 Tester
    """)

    chat = gr.Chatbot(
        height=600,
        avatar_images=("👤", "🤖"),
        render_markdown=True,
    )

    msg_box = gr.Textbox(
        placeholder="Create a calculator class with add, subtract, multiply, divide...",
        label="Your Requirement",
        lines=2,
    )
    send_btn = gr.Button("🚀 Build", variant="primary", size="lg")

    send_btn.click(handle_chat, [msg_box, chat], [msg_box, chat])

    gr.Examples([
        ["Create a hello world function"],
        ["Create a calculator class with add, subtract, multiply, divide"],
        ["Write a function to check if a number is prime"],
        ["Create a simple stack data structure"],
    ], [msg_box])

    gr.Markdown("""
    ### How It Works
    1. **Planner** receives your requirement and creates an implementation plan
    2. **Coder** receives the plan and generates the code
    3. **Linter** checks the code for style issues
    4. **Reviewer** reviews the code for quality and logic
    5. **Fixer** applies fixes to identified issues
    6. **Tester** generates unit tests
    """)


if __name__ == "__main__":
    print("🚀 Starting AI Coder Multi-Agent System...")
    print("📍 http://localhost:7860")
    demo.launch(server_port=7860, show_error=True)
