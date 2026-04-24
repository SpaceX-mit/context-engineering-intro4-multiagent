"""AI Coder Streamlit App."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agents.aicoder.tools import extract_code_blocks, execute_code

st.set_page_config(page_title="AI Coder", page_icon="🧠")

st.title("🧠 AI Coder - Multi-Agent Code System")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.header("Quick Actions")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input
if prompt := st.chat_input("Describe what you want to build..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            try:
                from agents.aicoder import get_aicoder_agent
                agent = get_aicoder_agent()
                import asyncio
                result = asyncio.run(agent.run(f"Generate Python code for: {prompt}\n\nProvide complete code in a markdown block."))
                response = result.output if hasattr(result, 'output') else str(result)

                # Try to run code
                code_blocks = extract_code_blocks(response)
                if code_blocks:
                    exec_result = execute_code(code_blocks[0])
                    if exec_result["success"]:
                        output = exec_result.get("stdout", "") or "(No output)"
                        response += f"\n\n▶️ **Output:**\n```\n{output}\n```"
                    else:
                        err = exec_result.get("error", {})
                        response += f"\n\n❌ **Error:** {err.get('message', 'Unknown')}"

            except Exception as e:
                response = f"# Error: {e}"

        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# Code Runner
st.divider()
st.header("🔧 Quick Code Runner")
code = st.text_area("Python Code", value="print('Hello, World!')", height=150)

if st.button("▶️ Run Code"):
    with st.spinner("Running..."):
        result = execute_code(code)
        if result["success"]:
            st.success(f"Output: {result.get('stdout', '') or '(No output)'}")
        else:
            st.error(f"Error: {result.get('error', {}).get('message', 'Unknown')}")