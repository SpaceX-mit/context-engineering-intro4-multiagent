"""Simplest Chat AI Coder - Minimal implementation."""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simple HTML page as fallback
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head><title>AI Coder</title></head>
<body>
<h1>AI Coder - Multi-Agent Code System</h1>
<p>To use: python3 -m webui.aicoder_app</p>
</body>
</html>
"""

def run_aicoder_sync(requirement: str) -> str:
    """Run AI Coder synchronously."""
    try:
        from agents.aicoder import get_aicoder_agent

        async def _run():
            agent = get_aicoder_agent()
            prompt = f"""Generate Python code for: {requirement}

Provide complete code in a markdown block."""

            result = await agent.run(prompt)
            return result.output if hasattr(result, 'output') else str(result)

        return asyncio.run(_run())
    except Exception as e:
        return f"# Error: {e}"

def run_code_direct(code: str) -> str:
    """Run code."""
    try:
        exec(code)
        return "✅ Success"
    except Exception as e:
        return f"❌ {e}"

# Test function
if __name__ == "__main__":
    print("Testing AI Coder...")
    result = run_aicoder_sync("hello world")
    print(result[:500] if len(result) > 500 else result)