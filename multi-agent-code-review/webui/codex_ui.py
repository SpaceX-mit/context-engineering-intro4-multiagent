"""AI Coder - Codex Desktop Style UI

Complete implementation with detailed multi-agent workflow showing each agent's input/output.
"""

import os
import sys
import re
import json
import asyncio
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, request, jsonify, Response
from flask_cors import CORS

from core.context import WorkflowContext
from core.orchestrator import WorkflowOrchestrator
from agents.planner.agent import get_planner_agent
from agents.coder.agent import get_coder_agent
from agents.reviewer.agent import get_reviewer_agent
from agents.linter.agent import get_linter_agent
from agents.fixer.agent import get_fixer_agent
from agents.test_agent.agent import get_tester_agent

app = Flask(__name__, template_folder='.')
CORS(app)


# ============================================================================
# Collaboration Events System
# ============================================================================

class CollaborationEvents:
    """Manages collaboration events for display."""

    def __init__(self):
        self._events = []
        self._lock = threading.Lock()
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
            return event

    def get_all(self):
        """Get all events."""
        with self._lock:
            return list(self._events)

    def clear(self):
        """Clear all events."""
        with self._lock:
            self._events.clear()


events = CollaborationEvents()

# ============================================================================
# Workflow Orchestrator Setup
# ============================================================================

orch = WorkflowOrchestrator()

async def setup_orchestrator_handlers():
    """Set up workflow handlers with event emission."""

    async def planner_handler(step_input, context):
        events.add("running", "Sam", "planner", "Creating plan...")
        requirement = step_input.data
        if isinstance(requirement, dict):
            requirement = requirement.get("requirement", str(requirement))
        plan = get_planner_agent().plan(requirement)
        events.add("completed", "Sam", "planner", f"Plan: {plan.overview[:50]}...")
        return plan.overview

    async def coder_handler(step_input, context):
        events.add("running", "Codey", "coder", "Writing code...")
        code = get_coder_agent().implement(context.requirement)
        events.add("completed", "Codey", "coder", f"Generated {len(code.splitlines())} lines")
        return code

    async def linter_handler(step_input, context):
        events.add("running", "Lint", "linter", "Checking style...")
        code = step_input.data
        if isinstance(code, dict):
            code = code.get("code", str(code))
        issues = get_linter_agent().lint(code)
        events.add("completed", "Lint", "linter", f"Found {len(issues)} issues")
        return issues

    async def reviewer_handler(step_input, context):
        events.add("running", "Robie", "reviewer", "Reviewing quality...")
        code = step_input.data
        if isinstance(code, dict):
            code = code.get("code", str(code))
        result = get_reviewer_agent().review(code)
        events.add("completed", "Robie", "reviewer", f"Score: {result.score}/100")
        return result.issues

    async def fixer_handler(step_input, context):
        events.add("running", "Fix", "fixer", "Applying fixes...")
        data = step_input.data
        if isinstance(data, dict):
            code = data.get("code", "")
            all_issues = data.get("issues", [])
        else:
            code = context.code or ""
            all_issues = []
        fixed = get_fixer_agent().fix(code, all_issues)
        events.add("completed", "Fix", "fixer", f"Applied {len(all_issues)} fixes")
        return fixed

    async def tester_handler(step_input, context):
        events.add("running", "Testy", "tester", "Generating tests...")
        code = step_input.data
        if isinstance(code, dict):
            code = code.get("fixed_code", str(code))
        tests = get_tester_agent().generate_tests(code)
        events.add("completed", "Testy", "tester", "Tests generated")
        return tests

    orch.register_step_handler("planner", "plan", planner_handler)
    orch.register_step_handler("coder", "implement", coder_handler)
    orch.register_step_handler("linter", "lint", linter_handler)
    orch.register_step_handler("reviewer", "review", reviewer_handler)
    orch.register_step_handler("fixer", "fix", fixer_handler)
    orch.register_step_handler("tester", "test", tester_handler)


# Initialize handlers on module load
asyncio.run(setup_orchestrator_handlers())

HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Coder - Multi-Agent IDE</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-purple: #a371f7;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --accent-yellow: #d29922;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
            font-size: 13px;
        }

        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 48px;
        }

        .header-left { display: flex; align-items: center; gap: 16px; }
        .logo { font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }
        .logo-icon {
            width: 24px; height: 24px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            border-radius: 4px;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px;
        }

        /* Main Container */
        .main-container {
            flex: 1;
            display: flex;
            overflow: hidden;
        }

        .chat-area {
            width: 500px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }

        .chat-header {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
        }

        .message { margin-bottom: 12px; }

        .message-user {
            display: flex;
            justify-content: flex-end;
        }

        .message-user .bubble {
            background: var(--accent-blue);
            color: white;
            padding: 8px 12px;
            border-radius: 12px 12px 4px 12px;
            max-width: 85%;
            font-size: 12px;
        }

        .message-assistant .bubble {
            background: var(--bg-tertiary);
            padding: 8px 12px;
            border-radius: 4px 12px 12px 12px;
            max-width: 90%;
            font-size: 12px;
        }

        .message-meta {
            font-size: 10px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        .chat-input-area {
            padding: 12px;
            border-top: 1px solid var(--border);
        }

        .chat-input-wrapper { display: flex; gap: 8px; }

        .chat-input {
            flex: 1;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 12px;
            color: var(--text-primary);
            font-size: 13px;
        }

        .chat-input:focus { outline: none; border-color: var(--accent-blue); }

        .chat-send {
            background: var(--accent-blue);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            cursor: pointer;
            font-size: 12px;
        }

        .chat-send:hover { background: #2563eb; }

        /* Agent Pipeline Panel */
        .pipeline-panel {
            width: 180px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }

        /* Collaboration Events Panel */
        .events-panel {
            width: 220px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }

        .events-header {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .events-content {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }

        .event-item {
            padding: 8px 10px;
            border-radius: 6px;
            margin-bottom: 6px;
            font-size: 11px;
            background: var(--bg-tertiary);
            border-left: 3px solid var(--text-secondary);
        }

        .event-spawned { border-left-color: var(--accent-green); }
        .event-closed { border-left-color: var(--accent-blue); }
        .event-running { border-left-color: var(--accent-orange); }
        .event-completed { border-left-color: var(--accent-green); }
        .event-waiting { border-left-color: var(--text-secondary); }
        .event-error { border-left-color: var(--accent-red); }

        .event-time {
            font-size: 9px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        .pipeline-header {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 12px;
        }

        .pipeline-content {
            flex: 1;
            padding: 12px;
            overflow-y: auto;
        }

        /* Agent Status Cards */
        .agent-card {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 8px;
        }

        .agent-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .agent-card-info {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .agent-card-icon {
            width: 24px; height: 24px;
            border-radius: 6px;
            display: flex; align-items: center; justify-content: center;
            font-size: 12px;
        }

        .agent-card-name {
            font-size: 12px;
            font-weight: 600;
        }

        .agent-card-status {
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: 500;
        }

        .status-waiting { background: #4b5563; color: white; }
        .status-running { background: var(--accent-blue); color: white; }
        .status-completed { background: var(--accent-green); color: white; }
        .status-error { background: var(--accent-red); color: white; }

        .agent-card-progress {
            height: 4px;
            background: var(--bg-primary);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 6px;
        }

        .agent-card-progress-bar {
            height: 100%;
            background: var(--accent-blue);
            transition: width 0.5s ease;
        }

        .agent-card-detail {
            font-size: 10px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* Workflow Pipeline Visualization */
        .pipeline-flow {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 8px 0;
        }

        .pipeline-step {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 8px;
            border-radius: 6px;
            background: var(--bg-tertiary);
            font-size: 11px;
        }

        .pipeline-step.active {
            background: rgba(59, 130, 246, 0.2);
            border: 1px solid var(--accent-blue);
        }

        .pipeline-step.completed {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid var(--accent-green);
        }

        .pipeline-step-icon {
            width: 18px; height: 18px;
            border-radius: 4px;
            display: flex; align-items: center; justify-content: center;
            font-size: 10px;
        }

        .pipeline-arrow {
            text-align: center;
            color: var(--text-secondary);
            font-size: 10px;
            padding: 2px 0;
        }

        /* Agent Workflow Panel */
        .workflow-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .workflow-header {
            padding: 10px 16px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 12px;
        }

        .workflow-content {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }

        .agent-step {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 12px;
            overflow: hidden;
        }

        .agent-step-header {
            padding: 10px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            background: var(--bg-tertiary);
        }

        .agent-step-header:hover { background: #2d333b; }

        .agent-info { display: flex; align-items: center; gap: 10px; }

        .agent-avatar {
            width: 28px; height: 28px;
            border-radius: 6px;
            display: flex; align-items: center; justify-content: center;
            font-size: 14px;
        }

        .coordinator { background: var(--accent-purple); }
        .planner { background: var(--accent-orange); }
        .coder { background: var(--accent-green); }
        .reviewer { background: var(--accent-red); }
        .linter { background: var(--accent-blue); }
        .fixer { background: var(--accent-yellow); }
        .tester { background: #6366f1; }

        .agent-name { font-weight: 600; font-size: 13px; }
        .agent-role { font-size: 11px; color: var(--text-secondary); }

        .agent-status {
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 500;
        }

        .status-waiting { background: #4b5563; color: white; }
        .status-running { background: var(--accent-blue); color: white; }
        .status-completed { background: var(--accent-green); color: white; }
        .status-error { background: var(--accent-red); color: white; }
        .status-skipped { background: #6b7280; color: white; }

        .agent-step-body {
            padding: 0;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease;
        }

        .agent-step-body.expanded {
            padding: 12px;
            max-height: 800px;
        }

        .step-section {
            margin-bottom: 12px;
        }

        .step-section:last-child { margin-bottom: 0; }

        .step-label {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .step-input, .step-output {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            white-space: pre-wrap;
            max-height: 150px;
            overflow-y: auto;
        }

        .step-output { border-color: var(--accent-green); }

        .code-block {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            white-space: pre-wrap;
            overflow-x: auto;
            max-height: 200px;
            overflow-y: auto;
        }

        /* Right panel - Code output */
        .code-panel {
            width: 400px;
            background: var(--bg-secondary);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }

        .code-header {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
        }

        .code-content {
            flex: 1;
            padding: 12px;
            overflow-y: auto;
        }

        .code-editor {
            width: 100%;
            height: 100%;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            color: var(--text-primary);
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 13px;
            line-height: 1.5;
            resize: none;
        }

        /* Status bar */
        .status-bar {
            background: var(--bg-tertiary);
            border-top: 1px solid var(--border);
            padding: 4px 12px;
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-secondary);
        }

        .status-item { display: flex; align-items: center; gap: 6px; }
        .status-dot { width: 6px; height: 6px; border-radius: 50%; }
        .status-dot.green { background: var(--accent-green); }
        .status-dot.blue { background: var(--accent-blue); }

        .btn {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            cursor: pointer;
        }

        .btn:hover { background: var(--border); }
        .btn-primary { background: var(--accent-blue); border-color: var(--accent-blue); color: white; }

        select {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <div class="logo">
                <div class="logo-icon">🧠</div>
                <span>AI Coder</span>
            </div>
            <select id="workflow-select">
                <option value="sequential">Sequential</option>
                <option value="concurrent">Concurrent</option>
                <option value="iterative">Iterative</option>
            </select>
        </div>
        <button class="btn btn-primary" onclick="clearWorkflow()">🗑️ Clear</button>
    </div>

    <div class="main-container">
        <!-- Agent Pipeline Panel -->
        <div class="pipeline-panel">
            <div class="pipeline-header">🔄 Agent Pipeline</div>
            <div class="pipeline-content">
                <div class="pipeline-flow" id="pipeline-flow">
                    <div class="pipeline-step" data-agent="coordinator">
                        <div class="pipeline-step-icon" style="background: var(--accent-purple);">🧠</div>
                        <span>Coordinator</span>
                    </div>
                    <div class="pipeline-arrow">↓</div>
                    <div class="pipeline-step" data-agent="planner">
                        <div class="pipeline-step-icon" style="background: var(--accent-orange);">📋</div>
                        <span>Planner</span>
                    </div>
                    <div class="pipeline-arrow">↓</div>
                    <div class="pipeline-step" data-agent="coder">
                        <div class="pipeline-step-icon" style="background: var(--accent-green);">💻</div>
                        <span>Coder</span>
                    </div>
                    <div class="pipeline-arrow">↓</div>
                    <div class="pipeline-step" data-agent="linter">
                        <div class="pipeline-step-icon" style="background: var(--accent-blue);">📝</div>
                        <span>Linter</span>
                    </div>
                    <div class="pipeline-arrow">↓</div>
                    <div class="pipeline-step" data-agent="reviewer">
                        <div class="pipeline-step-icon" style="background: var(--accent-red);">🔍</div>
                        <span>Reviewer</span>
                    </div>
                    <div class="pipeline-arrow">↓</div>
                    <div class="pipeline-step" data-agent="tester">
                        <div class="pipeline-step-icon" style="background: #6366f1;">🧪</div>
                        <span>Tester</span>
                    </div>
                </div>

                <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border);">
                    <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">AGENT STATUS</div>
                    <div id="agent-status-list">
                        <div class="agent-card" data-agent="coordinator">
                            <div class="agent-card-header">
                                <div class="agent-card-info">
                                    <div class="agent-card-icon" style="background: var(--accent-purple);">🧠</div>
                                    <div class="agent-card-name">Coordinator</div>
                                </div>
                                <span class="agent-card-status status-waiting">Waiting</span>
                            </div>
                            <div class="agent-card-progress"><div class="agent-card-progress-bar" style="width: 0%"></div></div>
                            <div class="agent-card-detail">Task coordination</div>
                        </div>
                        <div class="agent-card" data-agent="planner">
                            <div class="agent-card-header">
                                <div class="agent-card-info">
                                    <div class="agent-card-icon" style="background: var(--accent-orange);">📋</div>
                                    <div class="agent-card-name">Planner</div>
                                </div>
                                <span class="agent-card-status status-waiting">Waiting</span>
                            </div>
                            <div class="agent-card-progress"><div class="agent-card-progress-bar" style="width: 0%"></div></div>
                            <div class="agent-card-detail">Task planning</div>
                        </div>
                        <div class="agent-card" data-agent="coder">
                            <div class="agent-card-header">
                                <div class="agent-card-info">
                                    <div class="agent-card-icon" style="background: var(--accent-green);">💻</div>
                                    <div class="agent-card-name">Coder</div>
                                </div>
                                <span class="agent-card-status status-waiting">Waiting</span>
                            </div>
                            <div class="agent-card-progress"><div class="agent-card-progress-bar" style="width: 0%"></div></div>
                            <div class="agent-card-detail">Code generation</div>
                        </div>
                        <div class="agent-card" data-agent="linter">
                            <div class="agent-card-header">
                                <div class="agent-card-info">
                                    <div class="agent-card-icon" style="background: var(--accent-blue);">📝</div>
                                    <div class="agent-card-name">Linter</div>
                                </div>
                                <span class="agent-card-status status-waiting">Waiting</span>
                            </div>
                            <div class="agent-card-progress"><div class="agent-card-progress-bar" style="width: 0%"></div></div>
                            <div class="agent-card-detail">Style checking</div>
                        </div>
                        <div class="agent-card" data-agent="reviewer">
                            <div class="agent-card-header">
                                <div class="agent-card-info">
                                    <div class="agent-card-icon" style="background: var(--accent-red);">🔍</div>
                                    <div class="agent-card-name">Reviewer</div>
                                </div>
                                <span class="agent-card-status status-waiting">Waiting</span>
                            </div>
                            <div class="agent-card-progress"><div class="agent-card-progress-bar" style="width: 0%"></div></div>
                            <div class="agent-card-detail">Quality assessment</div>
                        </div>
                        <div class="agent-card" data-agent="tester">
                            <div class="agent-card-header">
                                <div class="agent-card-info">
                                    <div class="agent-card-icon" style="background: #6366f1;">🧪</div>
                                    <div class="agent-card-name">Tester</div>
                                </div>
                                <span class="agent-card-status status-waiting">Waiting</span>
                            </div>
                            <div class="agent-card-progress"><div class="agent-card-progress-bar" style="width: 0%"></div></div>
                            <div class="agent-card-detail">Test generation</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Collaboration Events Panel -->
        <div class="events-panel">
            <div class="events-header">
                <span>✦ Events</span>
                <button class="btn" onclick="clearEvents()">Clear</button>
            </div>
            <div class="events-content" id="events-container">
                <div style="text-align: center; color: var(--text-secondary); padding: 20px 0; font-size: 11px;">
                    No events yet
                </div>
            </div>
        </div>

        <!-- Chat Area -->
        <div class="chat-area">
            <div class="chat-header">
                <span>💬 Chat</span>
                <span id="agent-count">7 agents ready</span>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="message message-assistant">
                    <div class="bubble">
                        <strong>AI Coder Ready!</strong><br>
                        Describe what you want to build. I'll show you the detailed workflow of each agent.
                    </div>
                    <div class="message-meta">System • Just now</div>
                </div>
            </div>
            <div class="chat-input-area">
                <div class="chat-input-wrapper">
                    <input type="text" class="chat-input" id="chat-input" placeholder="Describe what you want to build...">
                    <button class="chat-send" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>

        <!-- Agent Workflow Panel -->
        <div class="workflow-panel">
            <div class="workflow-header">
                📋 Multi-Agent Workflow - Detailed View
            </div>
            <div class="workflow-content" id="workflow-content">
                <div style="text-align: center; color: var(--text-secondary); padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
                    <div>Send a message to see the multi-agent workflow</div>
                    <div style="font-size: 11px; margin-top: 8px;">Each agent's input/output will be displayed here</div>
                </div>
            </div>
        </div>

        <!-- Code Panel -->
        <div class="code-panel">
            <div class="code-header">
                <span>📄 Generated Code</span>
                <button class="btn" onclick="copyCode()">📋 Copy</button>
            </div>
            <div class="code-content">
                <textarea class="code-editor" id="code-editor" placeholder="Generated code will appear here..."></textarea>
            </div>
        </div>
    </div>

    <div class="status-bar">
        <div style="display: flex; gap: 16px;">
            <div class="status-item"><span class="status-dot green"></span> Ready</div>
            <div class="status-item">Model: llama3.2</div>
        </div>
        <div style="display: flex; gap: 16px;">
            <div class="status-item">7 agents available</div>
        </div>
    </div>

    <script>
        let workflowSteps = [];
        let eventSource = null;

        // Connect to SSE for real-time events
        function connectEventSource() {
            if (eventSource) eventSource.close();
            eventSource = new EventSource('/api/events/stream');
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addEvent(data);
                updatePipelineFromEvent(data);
            };
            eventSource.onerror = function() {
                // Reconnect after 2 seconds
                setTimeout(connectEventSource, 2000);
            };
        }

        function addEvent(event) {
            const container = document.getElementById('events-container');
            if (!container) return;

            // Remove placeholder if present
            const placeholder = container.querySelector('div[style*="text-align"]');
            if (placeholder) placeholder.remove();

            const icons = {
                'spawned': '✦',
                'closed': '✓',
                'running': '◐',
                'completed': '✓',
                'waiting': '⏳',
                'error': '❌'
            };

            const time = new Date(event.timestamp).toLocaleTimeString();

            const html = `
                <div class="event-item event-${event.type}">
                    ${icons[event.type] || '•'} <strong>${event.agent}</strong> [${event.role}]
                    <br>${event.message}
                    <div class="event-time">${time}</div>
                </div>
            `;

            container.insertAdjacentHTML('afterbegin', html);

            // Keep only last 30 events
            const events = container.querySelectorAll('.event-item');
            if (events.length > 30) {
                events[events.length - 1].remove();
            }
        }

        function updatePipelineFromEvent(event) {
            const role = event.role;
            const pipelineItem = document.querySelector(`.pipeline-step[data-agent="${role}"]`);

            if (pipelineItem) {
                if (event.type === 'running') {
                    pipelineItem.classList.add('active');
                    pipelineItem.style.opacity = '1';
                } else if (event.type === 'completed' || event.type === 'closed') {
                    pipelineItem.classList.remove('active');
                    pipelineItem.style.opacity = '0.7';
                }
            }
        }

        function clearEvents() {
            fetch('/api/events/clear', { method: 'POST' })
                .then(() => {
                    const container = document.getElementById('events-container');
                    if (container) {
                        container.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 20px 0; font-size: 11px;">No events yet</div>';
                    }
                    // Reset pipeline
                    document.querySelectorAll('.pipeline-step').forEach(el => {
                        el.classList.remove('active');
                        el.style.opacity = '1';
                    });
                });
        }

        // Initialize SSE connection
        connectEventSource();

        document.getElementById('chat-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;

            addMessage('user', message);
            input.value = '';

            addMessage('assistant', '🔄 Starting multi-agent workflow...', 'System');

            // Reset all agent statuses
            resetAgentStatuses();

            // Start pipeline animation
            animatePipeline();

            try {
                const response = await fetch('/generate_detailed', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        prompt: message,
                        workflow: document.getElementById('workflow-select').value
                    })
                });

                const data = await response.json();

                if (data.error) {
                    addMessage('assistant', '❌ Error: ' + data.error, 'System');
                    return;
                }

                // Update agent statuses based on workflow steps
                updateAgentStatuses(data.workflow_steps);

                // Clear previous workflow
                document.getElementById('workflow-content').innerHTML = '';
                workflowSteps = [];

                // Add workflow steps
                for (const step of data.workflow_steps) {
                    addWorkflowStep(step);
                }

                // Update final code
                if (data.final_code) {
                    document.getElementById('code-editor').value = data.final_code;
                }

                // Show summary
                addMessage('assistant',
                    `✅ Workflow completed!\n\n` +
                    `Agents involved: ${data.stats.agents_count}\n` +
                    `Steps executed: ${data.stats.steps_count}\n` +
                    `Code lines: ${data.stats.code_lines}`,
                    'System'
                );

            } catch (err) {
                addMessage('assistant', '❌ Error: ' + err, 'System');
            }
        }

        function addWorkflowStep(step) {
            const container = document.getElementById('workflow-content');

            const statusClass = {
                'pending': 'status-waiting',
                'running': 'status-running',
                'completed': 'status-completed',
                'error': 'status-error',
                'skipped': 'status-skipped'
            }[step.status] || 'status-waiting';

            const avatarClass = step.agent.toLowerCase();

            const html = `
                <div class="agent-step" id="step-${step.step_num}">
                    <div class="agent-step-header" onclick="toggleStep('step-${step.step_num}')">
                        <div class="agent-info">
                            <div class="agent-avatar ${avatarClass}">${step.icon}</div>
                            <div>
                                <div class="agent-name">${step.agent}</div>
                                <div class="agent-role">${step.role}</div>
                            </div>
                        </div>
                        <span class="agent-status ${statusClass}">${step.status.toUpperCase()}</span>
                    </div>
                    <div class="agent-step-body" id="body-step-${step.step_num}">
                        <div class="step-section">
                            <div class="step-label">📥 Input</div>
                            <div class="step-input">${escapeHtml(step.input)}</div>
                        </div>
                        <div class="step-section">
                            <div class="step-label">📤 Output</div>
                            <div class="step-output">${escapeHtml(step.output)}</div>
                        </div>
                        ${step.code ? `
                        <div class="step-section">
                            <div class="step-label">💻 Generated Code</div>
                            <div class="code-block">${escapeHtml(step.code)}</div>
                        </div>` : ''}
                    </div>
                </div>
            `;

            container.insertAdjacentHTML('beforeend', html);

            // Auto expand completed steps
            if (step.status === 'completed') {
                setTimeout(() => {
                    document.getElementById('body-step-' + step.step_num).classList.add('expanded');
                }, step.step_num * 300);
            }
        }

        function toggleStep(stepId) {
            const body = document.getElementById('body-' + stepId);
            body.classList.toggle('expanded');
        }

        function addMessage(role, content, agent = 'Assistant') {
            const chat = document.getElementById('chat-messages');
            const time = new Date().toLocaleTimeString();

            const html = `
                <div class="message message-${role}">
                    <div class="bubble">${formatContent(content)}</div>
                    <div class="message-meta">${agent} • ${time}</div>
                </div>
            `;
            chat.insertAdjacentHTML('beforeend', html);
            chat.scrollTop = chat.scrollHeight;
        }

        function formatContent(text) {
            let html = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html = html.replace(/```python\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
            html = html.replace(/```\n?([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
            html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            html = html.replace(/\n/g, '<br>');
            return html;
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
        }

        function copyCode() {
            const code = document.getElementById('code-editor').value;
            navigator.clipboard.writeText(code);
            alert('Code copied!');
        }

        function clearWorkflow() {
            document.getElementById('workflow-content').innerHTML = `
                <div style="text-align: center; color: var(--text-secondary); padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
                    <div>Send a message to see the multi-agent workflow</div>
                    <div style="font-size: 11px; margin-top: 8px;">Each agent's input/output will be displayed here</div>
                </div>
            `;
            document.getElementById('chat-messages').innerHTML = `
                <div class="message message-assistant">
                    <div class="bubble">
                        <strong>AI Coder Ready!</strong><br>
                        Describe what you want to build.
                    </div>
                    <div class="message-meta">System • Just now</div>
                </div>
            `;
            document.getElementById('code-editor').value = '';
            resetAgentStatuses();
        }

        function resetAgentStatuses() {
            const agents = ['coordinator', 'planner', 'coder', 'linter', 'reviewer', 'tester'];
            agents.forEach(agent => {
                updateAgentCard(agent, 'waiting', 0);
                updatePipelineStep(agent, '');
            });
        }

        function updateAgentCard(agent, status, progress) {
            const card = document.querySelector(`.agent-card[data-agent="${agent}"]`);
            if (!card) return;

            const statusEl = card.querySelector('.agent-card-status');
            const progressBar = card.querySelector('.agent-card-progress-bar');

            statusEl.className = `agent-card-status status-${status}`;
            statusEl.textContent = status === 'waiting' ? 'Waiting' :
                                  status === 'running' ? 'Running' :
                                  status === 'completed' ? 'Done' :
                                  status === 'error' ? 'Error' : status;

            if (progressBar) {
                progressBar.style.width = progress + '%';
            }
        }

        function updatePipelineStep(agent, status) {
            const step = document.querySelector(`.pipeline-step[data-agent="${agent}"]`);
            if (!step) return;

            step.classList.remove('active', 'completed');
            if (status === 'running') {
                step.classList.add('active');
            } else if (status === 'completed') {
                step.classList.add('completed');
            }
        }

        function updateAgentStatuses(workflowSteps) {
            workflowSteps.forEach((step, index) => {
                const agentName = step.agent.toLowerCase();

                // Delay to simulate sequential execution
                setTimeout(() => {
                    // Update to running
                    updateAgentCard(agentName, 'running', 50);
                    updatePipelineStep(agentName, 'running');
                }, index * 200);

                // Update to completed
                setTimeout(() => {
                    updateAgentCard(agentName, 'completed', 100);
                    updatePipelineStep(agentName, 'completed');
                }, index * 200 + 300);
            });
        }

        function animatePipeline() {
            const agents = ['coordinator', 'planner', 'coder', 'linter', 'reviewer', 'tester'];
            let currentIndex = 0;

            const interval = setInterval(() => {
                if (currentIndex > 0 && currentIndex <= agents.length) {
                    updatePipelineStep(agents[currentIndex - 1], 'completed');
                }

                if (currentIndex < agents.length) {
                    updatePipelineStep(agents[currentIndex], 'running');
                    updateAgentCard(agents[currentIndex], 'running', 30);
                } else {
                    clearInterval(interval);
                }

                currentIndex++;
            }, 400);
        }
    </script>
</body>
</html>
'''


def execute_code_safe(code: str) -> dict:
    """Execute Python code safely in sandbox."""
    import io
    import sys

    stdout_c = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_c

    result = {"success": True, "output": "", "error": None}

    RESTRICTED_BUILTINS = {
        "print": print, "len": len, "range": range, "str": str,
        "int": int, "float": float, "list": list, "dict": dict,
        "set": set, "tuple": tuple, "bool": bool,
        "True": True, "False": False, "None": None,
        "enumerate": enumerate, "zip": zip, "sorted": sorted,
        "sum": sum, "min": min, "max": max, "abs": abs,
        "isinstance": isinstance, "type": type,
    }

    try:
        namespace = {"__name__": "__aicoder__", "__builtins__": RESTRICTED_BUILTINS}
        exec(code, namespace)
        result["output"] = stdout_c.getvalue()
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    finally:
        sys.stdout = old_stdout

    return result


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/generate_detailed', methods=['POST'])
def generate_detailed():
    """Generate code with detailed multi-agent workflow showing each agent's input/output."""
    data = request.json
    prompt = data.get('prompt', '')
    workflow_type = data.get('workflow', 'sequential')

    async def run_workflow():
        from agent_framework import Agent
        from agent_framework.ollama import OllamaChatClient

        client = OllamaChatClient(model='llama3.2')
        workflow_steps = []
        final_code = ""

        # Agent configurations
        agents_config = {
            'coordinator': {
                'name': 'Coordinator',
                'icon': '🧠',
                'role': 'Task decomposition and coordination',
                'prompt': '''You are the Coordinator Agent. Parse the user's requirement and break it down into tasks.

User Request: {requirement}

Output a brief task list (3-5 items max) for other agents to follow.'''
            },
            'planner': {
                'name': 'Planner',
                'icon': '📋',
                'role': 'Project planning and task breakdown',
                'prompt': '''You are the Planner Agent. Create a detailed implementation plan.

Requirement: {requirement}

Output a numbered plan with: 1) Files to create 2) Implementation steps 3) Dependencies'''
            },
            'coder': {
                'name': 'Coder',
                'icon': '💻',
                'role': 'Code generation and implementation',
                'prompt': '''You are the Coder Agent. Write complete, working Python code.

Requirement: {requirement}

Write clean Python code with type hints and docstrings. Output ONLY the code in a ```python``` block.'''
            },
            'linter': {
                'name': 'Linter',
                'icon': '📝',
                'role': 'Code style checking and formatting',
                'prompt': '''You are the Linter Agent. Check code for style issues.

Code to check: {code}

List any style issues found (or say "No issues found").'''
            },
            'reviewer': {
                'name': 'Reviewer',
                'icon': '🔍',
                'role': 'Code quality assessment',
                'prompt': '''You are the Reviewer Agent. Review code quality.

Code to review: {code}

Check for: 1) Logic errors 2) Security issues 3) Edge cases. Give a brief assessment.'''
            },
            'tester': {
                'name': 'Tester',
                'icon': '🧪',
                'role': 'Test generation',
                'prompt': '''You are the Tester Agent. Generate pytest tests.

Code to test: {code}

Write pytest test functions covering main functionality. Output in ```python``` block.'''
            },
            'fixer': {
                'name': 'Fixer',
                'icon': '🔧',
                'role': 'Problem repair and optimization',
                'prompt': '''You are the Fixer Agent. Fix any issues in the code.

Code with issues: {code}
Issues: {issues}

Provide the fixed code in a ```python``` block.'''
            }
        }

        # Step 1: Coordinator
        step_num = 1
        coord_cfg = agents_config['coordinator']
        coord_prompt = coord_cfg['prompt'].format(requirement=prompt)

        coordinator = Agent(client=client, name=coord_cfg['name'],
                           instructions="You are the Coordinator. Be concise.")
        coord_result = await coordinator.run(coord_prompt)
        coord_output = coord_result.text if hasattr(coord_result, 'text') else str(coord_result)

        workflow_steps.append({
            'step_num': step_num,
            'agent': coord_cfg['name'],
            'icon': coord_cfg['icon'],
            'role': coord_cfg['role'],
            'status': 'completed',
            'input': f"Parse requirement: {prompt}",
            'output': coord_output[:500] + '...' if len(coord_output) > 500 else coord_output,
            'code': None
        })
        step_num += 1

        # Step 2: Planner
        plan_cfg = agents_config['planner']
        plan_prompt = plan_cfg['prompt'].format(requirement=prompt)

        planner = Agent(client=client, name=plan_cfg['name'],
                       instructions="You are the Planner. Be concise and practical.")
        plan_result = await planner.run(plan_prompt)
        plan_output = plan_result.text if hasattr(plan_result, 'text') else str(plan_result)

        workflow_steps.append({
            'step_num': step_num,
            'agent': plan_cfg['name'],
            'icon': plan_cfg['icon'],
            'role': plan_cfg['role'],
            'status': 'completed',
            'input': f"Create plan for: {prompt}",
            'output': plan_output[:500] + '...' if len(plan_output) > 500 else plan_output,
            'code': None
        })
        step_num += 1

        # Step 3: Coder
        coder_cfg = agents_config['coder']
        coder_prompt = coder_cfg['prompt'].format(requirement=prompt)

        coder = Agent(client=client, name=coder_cfg['name'],
                     instructions="You are the Coder. Write clean, working Python code.")
        coder_result = await coder.run(coder_prompt)
        coder_output = coder_result.text if hasattr(coder_result, 'text') else str(coder_result)

        # Extract code
        code_match = re.search(r'```python\n([\s\S]*?)```', coder_output, re.DOTALL)
        extracted_code = code_match.group(1).strip() if code_match else ""

        workflow_steps.append({
            'step_num': step_num,
            'agent': coder_cfg['name'],
            'icon': coder_cfg['icon'],
            'role': coder_cfg['role'],
            'status': 'completed',
            'input': f"Write code for: {prompt}",
            'output': "Code generated successfully",
            'code': extracted_code
        })
        final_code = extracted_code
        step_num += 1

        # Step 4: Linter (in parallel with Reviewer)
        lint_cfg = agents_config['linter']
        lint_prompt = lint_cfg['prompt'].format(code=extracted_code[:500] if extracted_code else "")

        linter = Agent(client=client, name=lint_cfg['name'],
                      instructions="You are the Linter. Check for style issues.")
        lint_result = await linter.run(lint_prompt)
        lint_output = lint_result.text if hasattr(lint_result, 'text') else str(lint_result)

        workflow_steps.append({
            'step_num': step_num,
            'agent': lint_cfg['name'],
            'icon': lint_cfg['icon'],
            'role': lint_cfg['role'],
            'status': 'completed',
            'input': f"Check style of {len(extracted_code)} chars",
            'output': lint_output[:300] + '...' if len(lint_output) > 300 else lint_output,
            'code': None
        })
        step_num += 1

        # Step 5: Reviewer
        rev_cfg = agents_config['reviewer']
        rev_prompt = rev_cfg['prompt'].format(code=extracted_code[:500] if extracted_code else "")

        reviewer = Agent(client=client, name=rev_cfg['name'],
                        instructions="You are the Reviewer. Check code quality.")
        rev_result = await reviewer.run(rev_prompt)
        rev_output = rev_result.text if hasattr(rev_result, 'text') else str(rev_result)

        workflow_steps.append({
            'step_num': step_num,
            'agent': rev_cfg['name'],
            'icon': rev_cfg['icon'],
            'role': rev_cfg['role'],
            'status': 'completed',
            'input': f"Review {len(extracted_code)} chars of code",
            'output': rev_output[:300] + '...' if len(rev_output) > 300 else rev_output,
            'code': None
        })
        step_num += 1

        # Step 6: Tester
        test_cfg = agents_config['tester']
        test_prompt = test_cfg['prompt'].format(code=extracted_code[:500] if extracted_code else "")

        tester = Agent(client=client, name=test_cfg['name'],
                       instructions="You are the Tester. Generate pytest tests.")
        test_result = await tester.run(test_prompt)
        test_output = test_result.text if hasattr(test_result, 'text') else str(test_result)

        # Extract test code
        test_match = re.search(r'```python\n([\s\S]*?)```', test_output, re.DOTALL)
        test_code = test_match.group(1).strip() if test_match else ""

        workflow_steps.append({
            'step_num': step_num,
            'agent': test_cfg['name'],
            'icon': test_cfg['icon'],
            'role': test_cfg['role'],
            'status': 'completed',
            'input': f"Generate tests for {len(extracted_code)} chars code",
            'output': "Tests generated for main functions" if test_code else "No testable functions found",
            'code': test_code
        })

        # Execute the main code
        exec_result = execute_code_safe(extracted_code)
        execution_output = exec_result.get("output") if exec_result["success"] else None

        return {
            'workflow_steps': workflow_steps,
            'final_code': final_code,
            'execution_output': execution_output,
            'stats': {
                'agents_count': len(workflow_steps),
                'steps_count': len(workflow_steps),
                'code_lines': len(final_code.split('\n')) if final_code else 0
            }
        }

    try:
        return asyncio.run(run_workflow())
    except Exception as e:
        return jsonify({
            'error': str(e),
            'workflow_steps': [],
            'final_code': None
        })


@app.route('/run', methods=['POST'])
def run():
    """Execute code."""
    data = request.json
    code = data.get('code', '')

    result = execute_code_safe(code)
    if result["success"]:
        return jsonify({"success": True, "output": result.get("output", "") or "(No output)"})
    return jsonify({"success": False, "error": result.get("error", "Unknown")})


@app.route('/agents/status', methods=['GET'])
def agents_status():
    """Get status of all agents."""
    return jsonify({
        "agents": [
            {"name": "Coordinator", "status": "ready", "role": "Task decomposition", "icon": "🧠"},
            {"name": "Planner", "status": "ready", "role": "Project planning", "icon": "📋"},
            {"name": "Coder", "status": "ready", "role": "Code generation", "icon": "💻"},
            {"name": "Linter", "status": "ready", "role": "Style checking", "icon": "📝"},
            {"name": "Reviewer", "status": "ready", "role": "Quality assessment", "icon": "🔍"},
            {"name": "Tester", "status": "ready", "role": "Test generation", "icon": "🧪"},
        ]
    })


# ============================================================================
# New Orchestrator-based Workflow API
# ============================================================================

@app.route('/api/workflow', methods=['POST'])
def run_workflow():
    """Run workflow using orchestrator with event tracking."""
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
def clear_events_api():
    """Clear all events."""
    events.clear()
    return jsonify({"success": True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)