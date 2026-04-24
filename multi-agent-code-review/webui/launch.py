"""Launch AI Coder Multi-Agent System."""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from core.context import WorkflowContext
from core.orchestrator import WorkflowOrchestrator
from agents.coordinator.agent import get_coordinator_agent
from agents.planner.agent import get_planner_agent
from agents.coder.agent import get_coder_agent
from agents.reviewer.agent import get_reviewer_agent
from agents.linter.agent import get_linter_agent
from agents.fixer.agent import get_fixer_agent
from agents.test_agent.agent import get_tester_agent


# Initialize orchestrator with handlers
orch = WorkflowOrchestrator()

async def planner_handler(context, step):
    plan = get_planner_agent().plan(context.requirement)
    context.set_plan(plan.overview)
    return {"plan": plan.overview}

async def coder_handler(context, step):
    code = get_coder_agent().implement(context.requirement)
    context.set_code(code)
    return {"code_generated": True}

async def linter_handler(context, step):
    issues = get_linter_agent().lint(context.code)
    context.lint_issues = issues
    return {"issues": len(issues)}

async def reviewer_handler(context, step):
    result = get_reviewer_agent().review(context.code)
    context.review_issues = result.issues
    return {"score": result.score, "issues": len(result.issues)}

async def fixer_handler(context, step):
    all_issues = context.lint_issues + context.review_issues
    fixed = get_fixer_agent().fix(context.code, all_issues)
    context.fixed_code = fixed
    return {"fixed": len(all_issues)}

async def tester_handler(context, step):
    tests = get_tester_agent().generate_tests(context.fixed_code or context.code)
    context.set_tests(tests)
    return {"tests_generated": True}

# Register handlers
orch.register_step_handler('planner', 'plan', planner_handler)
orch.register_step_handler('coder', 'implement', coder_handler)
orch.register_step_handler('linter', 'lint', linter_handler)
orch.register_step_handler('reviewer', 'review', reviewer_handler)
orch.register_step_handler('fixer', 'fix', fixer_handler)
orch.register_step_handler('tester', 'test', tester_handler)


def run_workflow(requirement: str) -> dict:
    """Run the development workflow."""
    ctx = WorkflowContext()
    ctx.set_requirement(requirement)

    # Get workflow
    workflows = orch.list_workflows()
    dev_workflow = next(w for w in workflows if w.name == 'DevelopmentWorkflow')

    # Run
    result = asyncio.run(orch.execute_workflow(dev_workflow.id, ctx))

    return {
        "status": result.status.value,
        "plan": ctx.plan,
        "code": ctx.code,
        "lint_issues": len(ctx.lint_issues),
        "review_issues": len(ctx.review_issues),
        "fixed_code": ctx.fixed_code,
        "tests": ctx.tests,
        "errors": result.errors,
    }


def handle_chat(message: str, history: list) -> tuple:
    """Handle chat message."""
    if not message.strip():
        return "", history

    history.append([message, "🤔 Analyzing requirement..."])

    try:
        result = run_workflow(message)

        response = f"""## ✅ Development Complete

**Status:** {result['status']}

### 📋 Plan
{result['plan']}

### 💻 Generated Code
```python
{result['code']}
```

### 📊 Review Results
- Lint issues: {result['lint_issues']}
- Review issues: {result['review_issues']}

### 🧪 Generated Tests
```python
{result['tests'] or 'No tests generated'}
```

"""

        if result['errors']:
            response += f"\n⚠️ **Errors:** {result['errors']}"

        history[-1] = [message, response]

    except Exception as e:
        history[-1] = [message, f"❌ Error: {str(e)}"]

    return "", history


# Create Gradio interface
with gr.Blocks(title="AI Coder - Multi-Agent System") as demo:
    gr.Markdown("""
    # 🧠 AI Coder - Multi-Agent Code Development System

    Describe what you want to build, and the system will:
    1. **Plan** - Create an implementation plan
    2. **Code** - Generate the code
    3. **Lint** - Check code style
    4. **Review** - Quality assessment
    5. **Fix** - Auto-fix issues
    6. **Test** - Generate tests
    """)

    with gr.Row():
        chat = gr.Chatbot(height=500, show_copy_button=True)
        with gr.Column(scale=1):
            gr.Markdown("### Agent Status")
            status = gr.JSON({"agents": ["Coordinator", "Planner", "Coder", "Linter", "Reviewer", "Fixer", "Tester"]})

    msg_box = gr.Textbox(placeholder="Create a calculator class...", label="Your Requirement")
    send_btn = gr.Button("🚀 Build", variant="primary")

    send_btn.click(handle_chat, [msg_box, chat], [msg_box, chat])

    gr.Examples([
        ["Create a hello world function"],
        ["Create a calculator class with add, subtract, multiply, divide"],
        ["Write a function to check if a number is prime"],
        ["Create a simple stack data structure"],
    ], [msg_box])


if __name__ == "__main__":
    print("🚀 Starting AI Coder Multi-Agent System...")
    print("📍 http://localhost:7860")
    demo.launch(server_port=7860, show_error=True)
