"""AI Coder with Collaboration Events - Flask App."""

import os
import sys
import json
import asyncio
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS

from core.context import WorkflowContext
from core.orchestrator import WorkflowOrchestrator
from agents.coordinator.agent import get_coordinator_agent
from agents.planner.agent import get_planner_agent
from agents.coder.agent import get_coder_agent
from agents.reviewer.agent import get_reviewer_agent
from agents.linter.agent import get_linter_agent
from agents.fixer.agent import get_fixer_agent
from agents.test_agent.agent import get_tester_agent

app = Flask(__name__)
CORS(app)


# Collaboration Events System
class EventType:
    SPAWNED = "spawned"
    CLOSED = "closed"
    INTERACTION = "interaction"
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"


class CollaborationEvents:
    """Manages collaboration events for display."""

    def __init__(self):
        self._events = []
        self._lock = threading.Lock()
        self._callbacks = []
        self._max_events = 100

    def add(self, event_type: str, agent: str, role: str, message: str):
        """Add a collaboration event."""
        with self._lock:
            event = {
                "type": event_type,
                "agent": agent,
                "role": role,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb(event)
                except:
                    pass

    def get_all(self):
        """Get all events."""
        with self._lock:
            return list(self._events)

    def clear(self):
        """Clear all events."""
        with self._lock:
            self._events.clear()


events = CollaborationEvents()


def format_event(event: dict) -> str:
    """Format event for display."""
    icons = {
        "spawned": "✦",
        "closed": "✓",
        "interaction": "→",
        "waiting": "⏳",
        "running": "◐",
        "completed": "✓",
    }
    icon = icons.get(event["type"], "•")
    agent = event["agent"]
    role = event["role"]
    return f'{icon} <strong>{agent}</strong> [{role}] {event["message"]}'


# Initialize orchestrator
orch = WorkflowOrchestrator()

async def setup_handlers():
    """Set up workflow handlers with event emission."""

    async def planner_handler(context, step):
        events.add("running", "Sam", "planner", "Creating plan...")
        await asyncio.sleep(0.3)
        plan = get_planner_agent().plan(context.requirement)
        context.set_plan(plan.overview)
        events.add("completed", "Sam", "planner", f"Plan: {plan.overview[:30]}...")
        return {"plan": plan.overview}

    async def coder_handler(context, step):
        events.add("running", "Codey", "coder", "Writing code...")
        await asyncio.sleep(0.4)
        code = get_coder_agent().implement(context.requirement)
        context.set_code(code)
        events.add("completed", "Codey", "coder", f"Generated {len(code.splitlines())} lines")
        return {"code_generated": True}

    async def linter_handler(context, step):
        events.add("running", "Lint", "linter", "Checking style...")
        await asyncio.sleep(0.2)
        issues = get_linter_agent().lint(context.code)
        context.lint_issues = issues
        events.add("completed", "Lint", "linter", f"Found {len(issues)} issues")
        return {"issues": len(issues)}

    async def reviewer_handler(context, step):
        events.add("running", "Robie", "reviewer", "Reviewing quality...")
        await asyncio.sleep(0.3)
        result = get_reviewer_agent().review(context.code)
        context.review_issues = result.issues
        events.add("completed", "Robie", "reviewer", f"Score: {result.score}/100")
        return {"score": result.score}

    async def fixer_handler(context, step):
        events.add("running", "Fix", "fixer", "Applying fixes...")
        await asyncio.sleep(0.3)
        all_issues = context.lint_issues + context.review_issues
        fixed = get_fixer_agent().fix(context.code, all_issues)
        context.fixed_code = fixed
        events.add("completed", "Fix", "fixer", f"Applied {len(all_issues)} fixes")
        return {"fixed": len(all_issues)}

    async def tester_handler(context, step):
        events.add("running", "Testy", "tester", "Generating tests...")
        await asyncio.sleep(0.3)
        tests = get_tester_agent().generate_tests(context.fixed_code or context.code)
        context.set_tests(tests)
        events.add("completed", "Testy", "tester", "Tests generated")
        return {"tests_generated": True}

    orch.register_step_handler("planner", "plan", planner_handler)
    orch.register_step_handler("coder", "implement", coder_handler)
    orch.register_step_handler("linter", "lint", linter_handler)
    orch.register_step_handler("reviewer", "review", reviewer_handler)
    orch.register_step_handler("fixer", "fix", fixer_handler)
    orch.register_step_handler("tester", "test", tester_handler)

# Setup handlers
asyncio.run(setup_handlers())


@app.route('/')
def index():
    """Main UI page."""
    return render_template('collab_ui.html')


@app.route('/api/workflow', methods=['POST'])
def run_workflow():
    """Run the development workflow."""
    data = request.json
    requirement = data.get('requirement', '')

    if not requirement:
        return jsonify({"error": "Requirement is required"}), 400

    # Clear previous events
    events.clear()

    # Emit spawn events
    events.add("spawned", "Alex", "coordinator", "Starting workflow")
    events.add("spawned", "Sam", "planner", "Ready")
    events.add("spawned", "Codey", "coder", "Ready")
    events.add("spawned", "Lint", "linter", "Ready")
    events.add("spawned", "Robie", "reviewer", "Ready")
    events.add("spawned", "Fix", "fixer", "Ready")
    events.add("spawned", "Testy", "tester", "Ready")

    # Run workflow
    ctx = WorkflowContext()
    ctx.set_requirement(requirement)

    workflows = orch.list_workflows()
    dev_workflow = next(w for w in workflows if w.name == "DevelopmentWorkflow")

    try:
        result = asyncio.run(orch.execute_workflow(dev_workflow.id, ctx))

        # Emit close events
        events.add("closed", "Alex", "coordinator", "Completed")
        events.add("closed", "Sam", "planner", "Completed")
        events.add("closed", "Codey", "coder", "Completed")
        events.add("closed", "Lint", "linter", "Completed")
        events.add("closed", "Robie", "reviewer", "Completed")
        events.add("closed", "Fix", "fixer", "Completed")
        events.add("closed", "Testy", "tester", "Completed")

        return jsonify({
            "success": True,
            "status": result.status.value,
            "context": {
                "plan": ctx.plan,
                "code": ctx.code,
                "lint_issues": len(ctx.lint_issues),
                "review_issues": len(ctx.review_issues),
                "fixed_code": ctx.fixed_code,
                "tests": ctx.tests,
            },
            "stats": {
                "steps_completed": result.steps_completed,
                "duration": result.duration_seconds,
            }
        })

    except Exception as e:
        events.add("error", "System", "system", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/api/events', methods=['GET'])
def get_events():
    """Get collaboration events."""
    return jsonify({"events": events.get_all()})


@app.route('/api/events/stream')
def event_stream():
    """SSE stream for real-time events."""
    def generate():
        seen = set()
        while True:
            current_events = events.get_all()
            for event in current_events:
                event_id = f"{event['timestamp']}:{event['type']}"
                if event_id not in seen:
                    seen.add(event_id)
                    yield f"data: {json.dumps(event)}\n\n"
            import time
            time.sleep(0.3)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )


@app.route('/api/events/clear', methods=['POST'])
def clear_events():
    """Clear all events."""
    events.clear()
    return jsonify({"success": True})


if __name__ == '__main__':
    print("🚀 AI Coder with Collaboration Events")
    print("📍 http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
