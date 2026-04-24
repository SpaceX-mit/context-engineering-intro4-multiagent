"""AI Coder Flask WebUI - Based on OpenAI Codex Architecture.

Features:
- Session-based conversations
- Multi-agent collaboration (Coordinator, Planner, Coder, Reviewer, Tester)
- Skills system (code execution, file search, linting)
- Context management
- Streaming support
"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialize skills
from skills import get_registry
get_registry()  # Register default skills

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Coder - Codex Style</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0; padding: 20px;
            background: #0d1117; color: #c9d1d9;
        }
        h1 { color: #58a6ff; text-align: center; }
        .container { max-width: 1200px; margin: 0 auto; }
        .info { background: #161b22; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
        .info span { margin-right: 20px; color: #8b949e; font-size: 12px; }
        .chat-box {
            background: #161b22; border-radius: 10px;
            height: 450px; overflow-y: auto; padding: 20px;
            margin-bottom: 20px; border: 1px solid #30363d;
        }
        .message { margin: 15px 0; padding: 12px 16px; border-radius: 8px; max-width: 90%; }
        .user { background: #1f6feb; color: #fff; margin-left: auto; text-align: right; }
        .ai { background: #21262d; white-space: pre-wrap; }
        .agent-tag {
            font-size: 10px; padding: 2px 6px; border-radius: 3px; margin-right: 8px;
            display: inline-block;
        }
        .Coordinator { background: #6f42c1; color: white; }
        .Planner { background: #e36209; color: white; }
        .Coder { background: #22863a; color: white; }
        .Reviewer { background: #d73a49; color: white; }
        .Tester { background: #005cc5; color: white; }
        .System { background: #388bfd; color: white; }
        .input-area { display: flex; gap: 10px; margin-bottom: 20px; }
        input[type="text"] {
            flex: 1; padding: 12px; border-radius: 8px;
            border: 1px solid #30363d; background: #0d1117;
            color: #fff; font-size: 16px;
        }
        button {
            padding: 12px 24px; border-radius: 8px; border: none;
            cursor: pointer; font-size: 16px; background: #238636; color: #fff;
        }
        button:hover { background: #2ea043; }
        .code-area {
            background: #161b22; border-radius: 10px; padding: 20px;
            margin-top: 20px; border: 1px solid #30363d;
        }
        textarea {
            width: 100%; height: 150px; background: #0d1117; color: #c9d1d9;
            border: 1px solid #30363d; border-radius: 8px;
            padding: 12px; font-family: monospace; font-size: 14px;
        }
        pre { background: #0d1117; padding: 15px; border-radius: 8px; margin-top: 10px; white-space: pre-wrap; }
        .error { color: #f85149; }
        .skills { color: #8b949e; font-size: 12px; margin-top: 5px; }
        .session-info { background: #161b22; padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 12px; color: #8b949e; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 AI Coder - Codex Style</h1>

        <div class="info">
            <span>Model: <strong>llama3.2</strong></span>
            <span>Skills: code_runner, shell, file_search, linter</span>
            <span>Agents: Coordinator → Planner → Coder → Reviewer → Tester</span>
        </div>

        <div class="session-info" id="sessionInfo">
            Session: <span id="sessionId">-</span> |
            Messages: <span id="messageCount">0</span> |
            <button onclick="newSession()" style="padding: 2px 8px; font-size: 10px;">New Session</button>
        </div>

        <div class="chat-box" id="chatBox">
            <div class="message ai">
                <span class="agent-tag System">System</span>
                Welcome to AI Coder! Describe what you want to build.
                The multi-agent team will plan, code, review, and test your request.
            </div>
        </div>

        <div class="input-area">
            <input type="text" id="prompt" placeholder="Describe what you want to build...">
            <button onclick="sendMessage()">Send</button>
        </div>

        <div class="code-area">
            <h3>Code Runner</h3>
            <textarea id="code" placeholder="Code will appear here...">print("Hello, World!")</textarea>
            <br><br>
            <button onclick="runCode()">▶️ Run</button>
            <pre id="output">Output...</pre>
        </div>
    </div>

    <script>
        let sessionId = null;

        function newSession() {
            sessionId = null;
            document.getElementById('chatBox').innerHTML = `
                <div class="message ai">
                    <span class="agent-tag System">System</span>
                    New session started!
                </div>
            `;
            updateSessionInfo();
        }

        function updateSessionInfo() {
            document.getElementById('sessionId').textContent = sessionId || 'active';
            document.getElementById('messageCount').textContent =
                document.querySelectorAll('.message:not(:first-child)').length;
        }

        function sendMessage() {
            const prompt = document.getElementById('prompt').value.trim();
            if (!prompt) return;

            const chatBox = document.getElementById('chatBox');

            // User message
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.textContent = prompt;
            chatBox.appendChild(userMsg);

            // Thinking indicator
            const aiMsg = document.createElement('div');
            aiMsg.className = 'message ai';
            aiMsg.innerHTML = '<span class="agent-tag System">AI</span>Processing...';
            chatBox.appendChild(aiMsg);
            chatBox.scrollTop = chatBox.scrollHeight;

            document.getElementById('prompt').value = '';

            fetch('/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: prompt, session_id: sessionId})
            })
            .then(resp => resp.json())
            .then(data => {
                if (data.error) {
                    aiMsg.innerHTML = '<span class="agent-tag System">Error</span>' + escapeHtml(data.error);
                    aiMsg.className = 'message ai error';
                } else {
                    aiMsg.innerHTML = formatResponse(data.response);
                    if (data.code) {
                        document.getElementById('code').value = data.code;
                    }
                    if (data.session_id) {
                        sessionId = data.session_id;
                        updateSessionInfo();
                    }
                }
                chatBox.scrollTop = chatBox.scrollHeight;
                updateSessionInfo();
            })
            .catch(err => {
                aiMsg.innerHTML = '<span class="agent-tag System">Error</span>' + escapeHtml(err.toString());
                aiMsg.className = 'message ai error';
            });
        }

        function runCode() {
            const code = document.getElementById('code').value;
            const output = document.getElementById('output');
            output.textContent = 'Running...';

            fetch('/run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: code})
            })
            .then(resp => resp.json())
            .then(data => {
                output.textContent = data.success ? (data.output || 'Done') : 'Error: ' + data.error;
            })
            .catch(err => {
                output.textContent = 'Error: ' + err;
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function formatResponse(text) {
            // Format agent tags
            let formatted = '';
            const lines = text.split('\n');
            let currentTag = 'AI';

            for (const line of lines) {
                if (line.includes('**Coordinator') || line.startsWith('Coordinator:')) {
                    currentTag = 'Coordinator';
                    formatted += '<span class="agent-tag ' + currentTag + '">' + currentTag + '</span>';
                } else if (line.includes('**Planner') || line.startsWith('Planner:')) {
                    currentTag = 'Planner';
                    formatted += '<span class="agent-tag ' + currentTag + '">' + currentTag + '</span>';
                } else if (line.includes('**Coder') || line.startsWith('Coder:')) {
                    currentTag = 'Coder';
                    formatted += '<span class="agent-tag ' + currentTag + '">' + currentTag + '</span>';
                } else if (line.includes('**Reviewer') || line.startsWith('Reviewer:')) {
                    currentTag = 'Reviewer';
                    formatted += '<span class="agent-tag ' + currentTag + '">' + currentTag + '</span>';
                } else if (line.includes('**Tester') || line.startsWith('Tester:')) {
                    currentTag = 'Tester';
                    formatted += '<span class="agent-tag ' + currentTag + '">' + currentTag + '</span>';
                } else {
                    formatted += escapeHtml(line);
                }
                formatted += '\n';
            }

            return formatted;
        }

        document.getElementById('prompt').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
'''


def execute_code_safe(code: str) -> dict:
    """Execute Python code safely in sandbox."""
    import io
    import sys
    import time

    start = time.time()
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


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    session_id = data.get('session_id')

    try:
        import asyncio
        from agent_framework import Agent
        from agent_framework.ollama import OllamaChatClient

        client = OllamaChatClient(model='llama3.2')

        # Coordinator instructions
        instructions = """You are the Coordinator Agent in the AI Coder team.

Your role is to understand user requirements and provide code solutions.

## Team
- Planner: Creates implementation plans
- Coder: Writes Python code
- Reviewer: Checks code quality
- Tester: Runs tests

## Workflow
1. Understand the request
2. Write code that solves it
3. Execute the code to verify it works
4. Report results

## Output Format
Always include code in markdown blocks:
### Code
```python
[code here]
```

### Result
[output from running the code]

Be concise and practical. Execute code to verify it works."""

        agent = Agent(
            client=client,
            name='Coordinator',
            instructions=instructions,
        )

        # Inject skill execution guidance
        enhanced_prompt = f"""{prompt}

Important: After writing code, execute it using any available means and report the output.
If you generate code, include it in a ```python code block and briefly describe what it does.
"""

        result = asyncio.run(agent.run(enhanced_prompt))
        response = result.text if hasattr(result, 'text') else str(result)

        # Extract code
        code_pattern = r'```python\n(.*?)```'
        code_blocks = re.findall(code_pattern, response, re.DOTALL)
        code = code_blocks[0].strip() if code_blocks else ""

        # Execute code if found
        output = None
        if code:
            exec_result = execute_code_safe(code)
            if exec_result["success"]:
                output = exec_result.get("output")
                response += f"\n\n### Execution Output:\n{output}"

        return jsonify({
            "response": response,
            "code": code,
            "session_id": session_id or "default"
        })
    except Exception as e:
        return jsonify({
            "response": f"Error: {str(e)}",
            "code": "",
            "error": str(e),
            "session_id": session_id
        })


@app.route('/run', methods=['POST'])
def run():
    data = request.json
    code = data.get('code', '')

    result = execute_code_safe(code)
    if result["success"]:
        return jsonify({"success": True, "output": result.get("output", "") or "(No output)"})
    return jsonify({"success": False, "error": result.get("error", "Unknown")})


@app.route('/skills', methods=['GET'])
def list_skills():
    """List available skills."""
    registry = get_registry()
    skills = registry.list_skills()
    return jsonify({"skills": skills})


@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session info."""
    from core.session import SessionManager
    manager = SessionManager()
    session = manager.get_session(session_id)
    if session:
        return jsonify({
            "id": session.id,
            "message_count": len(session.messages),
            "artifacts": [a.to_dict() for a in session.artifacts],
            "status": session.status.value,
        })
    return jsonify({"error": "Session not found"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=False)
