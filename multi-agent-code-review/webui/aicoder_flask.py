"""AI Coder Flask App - Using Microsoft Agent Framework."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Coder - agent-framework</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #0d1117; color: #c9d1d9; }
        h1 { color: #58a6ff; text-align: center; }
        .container { max-width: 1000px; margin: 0 auto; }
        .chat-box { background: #161b22; border-radius: 10px; height: 400px; overflow-y: auto; padding: 20px; margin-bottom: 20px; border: 1px solid #30363d; }
        .message { margin: 10px 0; padding: 12px 16px; border-radius: 8px; max-width: 85%; white-space: pre-wrap; }
        .user { background: #1f6feb; color: #fff; margin-left: auto; text-align: right; }
        .ai { background: #21262d; }
        .agent-tag { font-size: 10px; padding: 2px 6px; border-radius: 3px; margin-right: 8px; }
        .Planner { background: #6f42c1; }
        .Coder { background: #22863a; }
        .AICoder { background: #005cc5; }
        .input-area { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; font-size: 16px; }
        button { padding: 12px 24px; border-radius: 8px; border: none; cursor: pointer; font-size: 16px; background: #238636; color: #fff; }
        button:hover { background: #2ea043; }
        .code-area { background: #161b22; border-radius: 10px; padding: 20px; margin-top: 20px; border: 1px solid #30363d; }
        textarea { width: 100%; height: 150px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 14px; }
        pre { background: #0d1117; padding: 15px; border-radius: 8px; margin-top: 10px; white-space: pre-wrap; }
        .error { color: #f85149; }
        .status { color: #8b949e; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 AI Coder</h1>
        <p class="status">Using: Ollama (llama3.2) + agent-framework</p>

        <div class="chat-box" id="chatBox">
            <div class="message ai"><span class="agent-tag AICoder">System</span>Hello! Describe what you want to build.</div>
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
        function sendMessage() {
            const prompt = document.getElementById('prompt').value.trim();
            if (!prompt) return;

            const chatBox = document.getElementById('chatBox');

            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.textContent = prompt;
            chatBox.appendChild(userMsg);

            const aiMsg = document.createElement('div');
            aiMsg.className = 'message ai';
            aiMsg.innerHTML = '<span class="agent-tag AICoder">AI</span>Thinking...';
            chatBox.appendChild(aiMsg);
            chatBox.scrollTop = chatBox.scrollHeight;

            document.getElementById('prompt').value = '';

            fetch('/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: prompt})
            })
            .then(resp => resp.json())
            .then(data => {
                if (data.error) {
                    aiMsg.innerHTML = '<span class="agent-tag AICoder">Error</span>' + escapeHtml(data.error);
                    aiMsg.className = 'message ai error';
                } else {
                    aiMsg.innerHTML = '<span class="agent-tag AICoder">AI</span>' + escapeHtml(data.response);
                    if (data.code) {
                        document.getElementById('code').value = data.code;
                    }
                }
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(err => {
                aiMsg.innerHTML = '<span class="agent-tag AICoder">Error</span>' + escapeHtml(err.toString());
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

        document.getElementById('prompt').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
'''


def execute_code_safe(code: str) -> dict:
    """Execute Python code safely."""
    import io
    import sys
    import time

    start = time.time()
    stdout_c = io.StringIO()

    old_stdout = sys.stdout
    sys.stdout = stdout_c

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
                "isinstance": isinstance, "type": type,
            },
        }
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

    try:
        import asyncio
        import re
        from agent_framework import Agent
        from agent_framework.ollama import OllamaChatClient

        client = OllamaChatClient(model='llama3.2')

        agent = Agent(
            client=client,
            name='AICoder',
            instructions='''You are an expert AI Coder. Write Python code for the user's request.

Write complete, working Python code in markdown blocks: ```python ... ```

Do NOT use any tools. Just write the code and explain briefly what it does.

Example:
User: hello world function
Response:
```python
def hello():
    print("Hello, World!")
```
This function prints a greeting.''',
        )

        result = asyncio.run(agent.run(prompt))
        response = result.text if hasattr(result, 'text') else str(result)

        # Extract code
        code_pattern = r'```python\n(.*?)```'
        code_blocks = re.findall(code_pattern, response, re.DOTALL)
        code = code_blocks[0].strip() if code_blocks else ""

        return jsonify({"response": response, "code": code})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}", "code": "", "error": str(e)})


@app.route('/run', methods=['POST'])
def run():
    data = request.json
    code = data.get('code', '')

    result = execute_code_safe(code)
    if result["success"]:
        return jsonify({"success": True, "output": result.get("output", "") or "(No output)"})
    return jsonify({"success": False, "error": result.get("error", "Unknown")})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=False)
