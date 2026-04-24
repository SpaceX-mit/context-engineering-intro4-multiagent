"""Simple HTML server as fallback."""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

os.chdir("/Users/duancheng/workspace2026/opencode-analysis/context-engineering-intro/multi-agent-code-review")

PORT = 7860

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Coder</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #1a1a2e; color: #fff; }
        h1 { color: #00d4ff; }
        .box { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
        button { background: #00d4ff; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background: #00a8cc; }
        textarea { width: 100%; height: 200px; background: #0f3460; color: #fff; border: 1px solid #00d4ff; border-radius: 5px; padding: 10px; }
        pre { background: #0f3460; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .status { color: #00ff88; }
    </style>
</head>
<body>
    <h1>🧠 AI Coder - Multi-Agent Code System</h1>

    <div class="box">
        <h2>Generate Code</h2>
        <textarea id="prompt" placeholder="Describe what you want to build...">Create a hello world function</textarea>
        <br>
        <button onclick="generate()">Generate Code</button>
        <button onclick="runCode()">▶️ Run Code</button>
    </div>

    <div class="box">
        <h2>Result</h2>
        <pre id="output">Output will appear here...</pre>
    </div>

    <div class="box">
        <h2>Code Runner</h2>
        <textarea id="code" placeholder="# Enter Python code...">print("Hello, World!")</textarea>
        <br>
        <button onclick="runDirect()">▶️ Run</button>
        <span id="status" class="status"></span>
    </div>

    <script>
        async function generate() {
            const prompt = document.getElementById("prompt").value;
            document.getElementById("output").textContent = "🤔 Generating...";

            try {
                const resp = await fetch("/api/generate", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({prompt: prompt})
                });
                const data = await resp.json();
                document.getElementById("code").value = data.code || data.error || "No response";
            } catch(e) {
                document.getElementById("output").textContent = "Error: " + e.message;
            }
        }

        async function runCode() {
            const code = document.getElementById("code").value;
            document.getElementById("status").textContent = "Running...";

            try {
                const resp = await fetch("/api/run", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({code: code})
                });
                const data = await resp.json();
                document.getElementById("output").textContent = data.output || data.error || "Done";
                document.getElementById("status").textContent = data.success ? "✅" : "❌";
            } catch(e) {
                document.getElementById("output").textContent = "Error: " + e.message;
            }
        }

        async function runDirect() {
            const code = document.getElementById("code").value;
            document.getElementById("status").textContent = "Running...";
            runCode();
        }
    </script>
</body>
</html>
            """
            self.wfile.write(html.encode())
        elif self.path == "/api/generate":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            import json
            self.wfile.write(json.dumps({"code": "# AI Code Generator ready\n# Use the webui.aicoder_app for full functionality"}).encode())
        elif self.path == "/api/run":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            import json
            self.wfile.write(json.dumps({"output": "Run endpoint ready", "success": True}).encode())
        else:
            super().do_GET()

print(f"Starting HTML server on port {PORT}...")
HTTPServer(("", PORT), Handler).serve_forever()