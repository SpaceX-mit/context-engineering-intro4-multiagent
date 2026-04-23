"""Gradio WebUI application for multi-agent code review system."""

import asyncio
import os
import sys
from typing import List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from webui.components import (
    create_chat_component,
    create_code_editor_component,
    create_file_browser_component,
    create_review_panel_component,
    ChatManager,
    CodeEditorManager,
    FileBrowserManager,
    ReviewPanelManager,
    format_issues_for_display,
    filter_issues,
    list_project_files,
    update_code_language,
)


# Global managers
chat_mgr = ChatManager()
editor_mgr = CodeEditorManager()
browser_mgr = FileBrowserManager()
review_mgr = ReviewPanelManager()


# Current project path
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", ".")


def load_file(filepath: str) -> Tuple[str, str]:
    """Load a file into the code editor."""
    content = editor_mgr.load_file(filepath)
    language = update_code_language(filepath)
    return content, language


def save_file(filepath: str, content: str) -> str:
    """Save file content."""
    return editor_mgr.save_file(filepath, content)


def refresh_files(root_path: str = None) -> List[str]:
    """Refresh file list."""
    if root_path:
        browser_mgr.root_path = root_path
    return browser_mgr.get_files()


async def run_agent_task(message: str, history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]]]:
    """Run agent task with streaming response."""
    if not message.strip():
        return "", history

    # Add user message to history
    history.append((message, ""))

    # Simulate async processing
    response_lines = []
    response_lines.append("🔄 **Processing request...**")

    # Import and run agent
    try:
        from agents import get_agent
        from agents.coder import coder_agent

        # Get the coder agent
        agent = coder_agent

        response_lines.append(f"🤖 **Agent**: Processing your request...")

        # Run the agent
        result = await agent.run(message)

        response = result.output if hasattr(result, "output") else str(result)
        response_lines.append(f"\n📝 **Result**:\n{response}")

        # Update review panel if applicable
        if "review" in message.lower() or "analyze" in message.lower():
            response_lines.append("\n🔍 **Analysis complete**")

    except Exception as e:
        response_lines.append(f"\n❌ **Error**: {str(e)}")

    # Join all response parts
    full_response = "\n".join(response_lines)
    history[-1] = (message, full_response)

    return "", history


def run_review_workflow(file_path: str, code: str) -> Tuple[List[List], dict]:
    """Run code review workflow."""
    if not code:
        return [], {}

    issues = []

    try:
        from tools.code_analysis import analyze_code_structure

        # Analyze code structure
        analysis = analyze_code_structure(code, "python")

        if "complexity" in analysis:
            complexity = analysis["complexity"]
            if complexity > 10:
                issues.append({
                    "file": file_path,
                    "line": "N/A",
                    "severity": "medium",
                    "type": "complexity",
                    "message": f"High cyclomatic complexity: {complexity}"
                })

        if "functions" in analysis:
            for func in analysis["functions"]:
                if func.get("nested_depth", 0) > 3:
                    issues.append({
                        "file": file_path,
                        "line": str(func.get("line", "N/A")),
                        "severity": "low",
                        "type": "complexity",
                        "message": f"Function '{func.get('name')}' has high nesting depth"
                    })

        # Security scan
        try:
            from tools.security import security_scan
            security_issues = security_scan(code, "python")
            for issue in security_issues:
                issues.append({
                    "file": file_path,
                    "line": str(issue.get("line", "N/A")),
                    "severity": issue.get("severity", "medium"),
                    "type": "security",
                    "message": issue.get("message", "Security issue")
                })
        except Exception:
            pass

        # Add issues to review manager
        review_mgr.add_issues(issues)

    except Exception as e:
        return [], {"error": str(e)}

    return format_issues_for_display(issues), review_mgr.get_summary()


def run_lint_check(code: str, file_path: str = "") -> str:
    """Run lint check on code."""
    try:
        from tools.linter import lint_code

        result = lint_code(code, "python")
        return result if result else "✅ No linting issues found"
    except Exception as e:
        return f"❌ Linting error: {str(e)}"


def generate_code(description: str, language: str = "python") -> str:
    """Generate code from description."""
    async def _generate():
        try:
            from agents.coder import coder_agent

            prompt = f"Generate {language} code for: {description}"
            result = await coder_agent.run(prompt)

            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            return f"Error generating code: {str(e)}"

    return asyncio.run(_generate())


def fix_code_issues(code: str, issues: List[dict]) -> str:
    """Fix code issues."""
    async def _fix():
        try:
            from agents.coder import coder_agent

            issues_text = "\n".join([
                f"- {issue.get('message', str(issue))}" for issue in issues
            ])

            prompt = f"""Fix the following code issues:

Issues:
{issues_text}

Original code:
```python
{code}
```
"""
            result = await coder_agent.run(prompt)

            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            return f"Error fixing code: {str(e)}"

    return asyncio.run(_fix())


def create_demo_interface() -> gr.Blocks:
    """Create the main demo interface."""
    with gr.Blocks(title="Multi-Agent Code Review System", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 🧠 Multi-Agent Code Review System

            A collaborative AI system for code development, review, and quality assurance.

            ## Features
            - **Code Generation**: Describe what you need, get working code
            - **Code Review**: Automatic analysis of code quality and issues
            - **Security Scanning**: Detect potential security vulnerabilities
            - **Style Checking**: Lint and format code automatically
            - **Fix Issues**: Let AI fix detected issues automatically

            ## Usage
            1. Write or paste code in the editor
            2. Use chat to request actions (review, generate, fix)
            3. View results in the review panel
            """
        )

        with gr.Tabs():
            with gr.TabItem("💬 Chat Interface"):
                chatbot, msg_input, send_btn = create_chat_component()

                send_btn.click(
                    fn=run_agent_task,
                    inputs=[msg_input, chatbot],
                    outputs=[msg_input, chatbot],
                )
                msg_input.submit(
                    fn=run_agent_task,
                    inputs=[msg_input, chatbot],
                    outputs=[msg_input, chatbot],
                )

            with gr.TabItem("📝 Code Editor"):
                with gr.Row():
                    file_selector, code_editor, save_btn, run_btn, clear_btn = create_code_editor_component()

                # File list
                file_list = gr.Dropdown(
                    choices=list_project_files(PROJECT_ROOT),
                    label="Project Files",
                    allow_custom_value=True,
                )

                file_list.change(
                    fn=load_file,
                    inputs=[file_list],
                    outputs=[code_editor],
                )
                file_list.change(
                    fn=update_code_language,
                    inputs=[file_list],
                    outputs=[code_editor],
                )

                save_btn.click(
                    fn=save_file,
                    inputs=[file_list, code_editor],
                    outputs=[],
                )

                with gr.Row():
                    review_btn = gr.Button("🔍 Run Review", variant="secondary")
                    lint_btn = gr.Button("✨ Lint Code", variant="secondary")

                review_output = gr.JSON(label="Review Summary")
                review_btn.click(
                    fn=run_review_workflow,
                    inputs=[file_list, code_editor],
                    outputs=[gr.Dataframe(visible=False), review_output],
                )

                lint_output = gr.Textbox(label="Lint Results", lines=5, show_label=False)
                lint_btn.click(
                    fn=run_lint_check,
                    inputs=[code_editor],
                    outputs=[lint_output],
                )

                # Generate code section (inline instead of modal)
                gr.Markdown("### Generate Code")
                with gr.Row():
                    gen_description = gr.Textbox(label="Code Description", lines=3, placeholder="Describe the code you want to generate...", scale=3)
                    gen_language = gr.Dropdown(
                        choices=["python", "javascript", "typescript", "go", "rust"],
                        value="python",
                        label="Language",
                        scale=1,
                    )
                gen_btn = gr.Button("Generate", variant="primary")
                gen_output = gr.Textbox(label="Generated Code", lines=15, show_label=False)

                gen_btn.click(
                    fn=generate_code,
                    inputs=[gen_description, gen_language],
                    outputs=[gen_output],
                )

            with gr.TabItem("📂 File Browser"):
                file_explorer, _, refresh_btn, _, _ = create_file_browser_component(
                    root_path=PROJECT_ROOT
                )

                refresh_btn.click(
                    fn=refresh_files,
                    inputs=[],
                    outputs=[file_list],
                )

            with gr.TabItem("🔍 Review Panel"):
                (issues_table, filter_severity, filter_type,
                 details_json, fix_selected_btn, fix_all_btn, export_btn) = create_review_panel_component()

                # Set up filtering
                filter_severity.change(
                    fn=lambda sev, typ: format_issues_for_display(
                        filter_issues(review_mgr.get_issues(), sev, typ)
                    ),
                    inputs=[filter_severity, filter_type],
                    outputs=[issues_table],
                )
                filter_type.change(
                    fn=lambda sev, typ: format_issues_for_display(
                        filter_issues(review_mgr.get_issues(), sev, typ)
                    ),
                    inputs=[filter_severity, filter_type],
                    outputs=[issues_table],
                )

                # Export functionality
                export_btn.click(
                    fn=review_mgr.export_report,
                    outputs=[details_json],
                )

    return demo


def create_api_interface() -> gr.Blocks:
    """Create interface with API backend."""
    try:
        import httpx

        with gr.Blocks(title="Multi-Agent Code Review API", theme=gr.themes.Soft()) as api_demo:
            gr.Markdown("# 🌐 API Client Interface")

            with gr.Row():
                api_url = gr.Textbox(
                    value="http://localhost:8000",
                    label="API URL",
                    scale=2,
                )
                health_btn = gr.Button("Check Health", scale=1)

            health_status = gr.JSON(label="API Health Status")
            health_btn.click(
                fn=lambda url: httpx.get(f"{url}/health").json() if url else {},
                inputs=[api_url],
                outputs=[health_status],
            )

            with gr.Tabs():
                with gr.TabItem("Analyze"):
                    with gr.Column():
                        analyze_code = gr.Code(label="Code to Analyze", language="python")
                        analyze_btn = gr.Button("Analyze", variant="primary")
                        analyze_result = gr.JSON(label="Analysis Results")

                        analyze_btn.click(
                            fn=lambda url, code: httpx.post(
                                f"{url}/api/analyze",
                                json={"code": code}
                            ).json(),
                            inputs=[api_url, analyze_code],
                            outputs=[analyze_result],
                        )

                with gr.TabItem("Review"):
                    with gr.Column():
                        review_code = gr.Code(label="Code to Review", language="python")
                        review_btn = gr.Button("Review", variant="primary")
                        review_result = gr.JSON(label="Review Results")

                        review_btn.click(
                            fn=lambda url, code: httpx.post(
                                f"{url}/api/review",
                                json={"code": code, "review_type": "full"}
                            ).json(),
                            inputs=[api_url, review_code],
                            outputs=[review_result],
                        )

                with gr.TabItem("Generate"):
                    with gr.Column():
                        gen_description = gr.Textbox(label="Description")
                        gen_btn = gr.Button("Generate", variant="primary")
                        gen_result = gr.JSON(label="Generated Code")

                        gen_btn.click(
                            fn=lambda url, desc: httpx.post(
                                f"{url}/api/generate",
                                json={"description": desc}
                            ).json(),
                            inputs=[api_url, gen_description],
                            outputs=[gen_result],
                        )

        return api_demo

    except ImportError:
        gr.Markdown("⚠️ `httpx` not installed. API client mode unavailable.")
        return None


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Agent Code Review WebUI")
    parser.add_argument("--mode", choices=["demo", "api"], default="demo", help="UI mode")
    parser.add_argument("--port", type=int, default=7860, help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--share", action="store_true", help="Create public link")
    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    # Set project root
    global PROJECT_ROOT
    PROJECT_ROOT = args.project_root

    # Update file browser
    browser_mgr = FileBrowserManager(args.project_root)

    if args.mode == "api":
        demo = create_api_interface()
    else:
        demo = create_demo_interface()

    demo.launch(
        server_port=args.port,
        server_name=args.host,
        share=args.share,
    )


if __name__ == "__main__":
    main()