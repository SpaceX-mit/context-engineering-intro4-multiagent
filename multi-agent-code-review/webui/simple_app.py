"""Simple WebUI application for multi-agent code review system."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from webui.components import (
    ChatManager,
    CodeEditorManager,
    ReviewPanelManager,
    format_issues_for_display,
)


# Global managers
chat_mgr = ChatManager()
editor_mgr = CodeEditorManager()
review_mgr = ReviewPanelManager()


def generate_code(description: str, language: str = "python") -> str:
    """Generate code from description using AI."""
    if not description.strip():
        return "# Please enter a description"

    try:
        from agents.coder import get_coder

        agent = get_coder()
        import asyncio
        result = asyncio.run(agent.run(f"""Generate {language} code for:

{description}

Requirements:
- Clean, well-documented code
- Follow best practices
- Include type hints
- Add docstrings

Provide only the code, no explanations."""))
        return result.output if hasattr(result, 'output') else str(result)
    except Exception as e:
        error_msg = str(e)
        if "llm_api_key" in error_msg.lower() or "required" in error_msg.lower():
            return "# ⚠️ Please set LLM_API_KEY in your .env file\n# Example: LLM_API_KEY=your-api-key-here"
        return f"# Error: {error_msg}"


def run_review(code: str) -> tuple:
    """Run code review."""
    if not code:
        return [], {}

    issues = []
    try:
        from tools.code_analysis import analyze_code_structure
        from tools.security import security_scan

        analysis = analyze_code_structure(code, "python")

        if "functions" in analysis:
            for func in analysis["functions"]:
                if func.get("nested_depth", 0) > 3:
                    issues.append({
                        "file": "",
                        "line": str(func.get("line", "N/A")),
                        "severity": "low",
                        "type": "complexity",
                        "message": f"High nesting depth in '{func.get('name')}'"
                    })

        security_issues = security_scan(code, "python")
        for issue in security_issues:
            issues.append({
                "file": "",
                "line": str(issue.get("line", "N/A")),
                "severity": issue.get("severity", "medium"),
                "type": "security",
                "message": issue.get("message", "Security issue")
            })

        review_mgr.clear_issues()
        review_mgr.add_issues(issues)

    except Exception as e:
        return [], {"error": str(e)}

    return format_issues_for_display(issues), review_mgr.get_summary()


def run_lint(code: str) -> str:
    """Run lint check."""
    try:
        from tools.linter import lint_code
        result = lint_code(code, "python")
        return result if result else "✅ No linting issues found"
    except Exception as e:
        return f"❌ Linting error: {str(e)}"


def fix_issues(code: str, issues_text: str) -> str:
    """Fix code issues."""
    if not code or not issues_text:
        return code

    try:
        from agents.coder import get_coder

        agent = get_coder()
        import asyncio
        result = asyncio.run(agent.run(f"""Fix the following code issues:

Issues:
{issues_text}

Original code:
```python
{code}
```

Provide the fixed code only."""))
        return result.output if hasattr(result, 'output') else str(result)
    except Exception as e:
        error_msg = str(e)
        if "llm_api_key" in error_msg.lower() or "required" in error_msg.lower():
            return f"# ⚠️ Please set LLM_API_KEY in your .env file\n{code}"
        return f"# Error fixing: {error_msg}\n{code}"


def create_demo_interface():
    """Create demo interface."""
    with gr.Blocks(title="Multi-Agent Code System") as demo:
        gr.Markdown("# 🧠 Multi-Agent Code Development System")

        with gr.Tabs():
            with gr.TabItem("📝 Code Editor"):
                gr.Markdown("### Write & Edit Code")
                code_editor = gr.Textbox(
                    value="# Enter code here...",
                    label="Code",
                    lines=15,
                )
                with gr.Row():
                    review_btn = gr.Button("🔍 Review", variant="primary")
                    lint_btn = gr.Button("✨ Lint")
                    fix_btn = gr.Button("🔧 Fix Issues")

                lint_result = gr.Textbox(label="Lint Results", lines=3, show_label=False)
                issues_output = gr.JSON(label="Review Results")

                review_btn.click(fn=run_review, inputs=[code_editor], outputs=[issues_output])
                lint_btn.click(fn=run_lint, inputs=[code_editor], outputs=[lint_result])
                fix_btn.click(
                    fn=lambda code, issues: fix_issues(code, str(issues)),
                    inputs=[code_editor, issues_output],
                    outputs=[code_editor],
                )

            with gr.TabItem("🎨 Generate Code"):
                gr.Markdown("### AI Code Generation")
                with gr.Row():
                    description = gr.Textbox(
                        label="Description",
                        placeholder="e.g., Create a calculator class with add, subtract, multiply, divide methods",
                        lines=3,
                        scale=3,
                    )
                    with gr.Column(scale=1):
                        language = gr.Dropdown(
                            choices=["python", "javascript", "typescript", "go", "rust"],
                            value="python",
                            label="Language",
                        )
                        generate_btn = gr.Button("🚀 Generate", variant="primary")

                generated_code = gr.Textbox(
                    label="Generated Code",
                    lines=20,
                    show_label=False,
                )
                with gr.Row():
                    copy_btn = gr.Button("📋 Copy to Editor")
                    save_btn = gr.Button("💾 Save")

                generated_code_state = gr.State("")

                def handle_generate(desc, lang):
                    code = generate_code(desc, lang)
                    return code, code

                generate_btn.click(
                    fn=handle_generate,
                    inputs=[description, language],
                    outputs=[generated_code, generated_code_state],
                )

            with gr.TabItem("🔍 Review Panel"):
                gr.Markdown("### Code Review Results")
                review_summary = gr.JSON(label="Summary")
                review_details = gr.Dataframe(
                    headers=["File", "Line", "Severity", "Type", "Message"],
                    label="Issues",
                )

    return demo


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Agent Code System")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")

    args = parser.parse_args()

    demo = create_demo_interface()
    demo.launch(
        server_port=args.port,
        share=args.share,
        show_error=True,
    )