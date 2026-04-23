"""Simple Chat AI Coder with Gradio."""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from agents.aicoder.tools import extract_code_blocks, execute_code


def run_aicoder(requirement: str) -> str:
    """Run AI Coder."""
    try:
        from agents.aicoder import get_aicoder_agent
        agent = get_aicoder_agent()
        result = asyncio.run(agent.run(f"Generate Python code for: {requirement}\n\nProvide complete code in a markdown block."))
        return result.output if hasattr(result, 'output') else str(result)
    except Exception as e:
        return f"# Error: {e}"

def handle_chat(message: str, history: list) -> tuple:
    """Handle chat."""
    if not message.strip():
        return "", history

    history.append([message, "🤔 Thinking..."])

    response = run_aicoder(message)

    # Try to run code
    code_blocks = extract_code_blocks(response)
    if code_blocks:
        exec_result = execute_code(code_blocks[0])
        if exec_result["success"]:
            output = exec_result.get("stdout", "") or "(No output)"
            response += f"\n\n▶️ Output:\n{output}"
        else:
            err = exec_result.get("error", {})
            response += f"\n\n❌ Error: {err.get('message', 'Unknown')}"

    history[-1] = [message, response]
    return "", history

def run_code(code: str) -> str:
    """Run code."""
    result = execute_code(code)
    if result["success"]:
        return result.get("stdout", "") or "Success"
    return f"Error: {result.get('error', {}).get('message', 'Unknown')}"

# Create interface
with gr.Blocks(title="AI Coder") as demo:
    gr.Markdown("# 🧠 AI Coder - Multi-Agent Code System")

    with gr.Row():
        chat = gr.Chatbot(height=400)
        with gr.Column(scale=1):
            gr.Markdown("### Quick Run")
            code_box = gr.Textbox(lines=8, label="Code", placeholder="# Python code")
            run_btn = gr.Button("▶️ Run", variant="primary")
            result_box = gr.Textbox(lines=6, label="Result")

    msg_box = gr.Textbox(placeholder="Describe what to build...", label="Your request")
    send_btn = gr.Button("Send", variant="primary")

    send_btn.click(handle_chat, [msg_box, chat], [msg_box, chat])
    run_btn.click(run_code, code_box, result_box)

    gr.Examples([
        ["Create a hello world function"],
        ["Create a calculator class"],
        ["Write a prime checker"],
    ], [msg_box])

demo.launch(server_port=7860, show_error=True)