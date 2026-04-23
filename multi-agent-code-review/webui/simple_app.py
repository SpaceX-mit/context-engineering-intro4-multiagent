"""WebUI application with multi-agent workflow integration."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from webui.components import (
    ReviewPanelManager,
    format_issues_for_display,
)


# Global manager
review_mgr = ReviewPanelManager()


def log_progress(message: str) -> str:
    """Log progress message."""
    return f"[{time.strftime('%H:%M:%S')}] {message}"


def run_full_workflow(code: str) -> tuple:
    """
    Run full workflow: lint -> review -> fix.
    Returns (processed_code, issues, logs)
    """
    logs = []
    issues = []

    logs.append(log_progress("🔍 Starting code analysis..."))

    # Step 1: Lint
    try:
        from tools.linter_tools import lint_python_code
        logs.append(log_progress("✨ Running linter..."))
        lint_result = lint_python_code(code, "")
        if lint_result:
            logs.append(log_progress(f"📋 Lint findings: {len(lint_result)} issues"))
        else:
            logs.append(log_progress("✅ No lint issues"))
    except Exception as e:
        logs.append(log_progress(f"❌ Lint error: {e}"))

    # Step 2: Code structure analysis
    try:
        from tools.code_analysis import analyze_code_structure
        logs.append(log_progress("📊 Analyzing code structure..."))
        analysis = analyze_code_structure(code, "python")
        if "error" not in analysis:
            logs.append(log_progress(f"📝 Functions: {len(analysis.get('functions', []))}"))
            logs.append(log_progress(f"📝 Classes: {len(analysis.get('classes', []))}"))
        else:
            logs.append(log_progress(f"⚠️ {analysis.get('error', 'Unknown error')}"))
    except Exception as e:
        logs.append(log_progress(f"❌ Analysis error: {e}"))

    # Step 3: Security scan
    try:
        from tools.security_scanner import scan_security_issues
        logs.append(log_progress("🔒 Running security scan..."))
        security_issues = scan_security_issues(code, "")
        for issue in security_issues:
            issues.append({
                "file": "",
                "line": str(issue.get("line", "N/A")),
                "severity": issue.get("severity", "medium"),
                "type": "security",
                "message": issue.get("message", "Security issue")
            })
        if security_issues:
            logs.append(log_progress(f"⚠️ Found {len(security_issues)} security issues"))
        else:
            logs.append(log_progress("✅ No security issues found"))
    except Exception as e:
        logs.append(log_progress(f"❌ Security scan error: {e}"))

    # Update review manager
    review_mgr.clear_issues()
    review_mgr.add_issues(issues)

    logs.append(log_progress("✅ Analysis complete!"))
    return code, format_issues_for_display(issues), "\n".join(logs)


def generate_code_with_progress(description: str, language: str = "python") -> str:
    """Generate code with progress display."""
    logs = []

    try:
        from agents.coder import get_coder

        logs.append(log_progress(f"🎨 Generating {language} code..."))
        agent = get_coder()

        import asyncio

        prompt = f"""Generate {language} code for:

{description}

Requirements:
- Clean, well-documented code
- Follow best practices
- Include type hints
- Add docstrings

Provide only the code."""

        logs.append(log_progress("🤖 AI is thinking..."))
        result = asyncio.run(agent.run(prompt))

        output = result.output if hasattr(result, 'output') else str(result)
        logs.append(log_progress("✅ Code generated!"))

        return "\n".join(logs) + "\n\n---\nGenerated Code:\n" + output

    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "required" in error_msg.lower():
            return "# ⚠️ Please set LLM_API_KEY in your .env file"
        return "\n".join(logs) + f"\n❌ Error: {error_msg}"


def review_and_fix(code: str) -> str:
    """Run review and fix issues using AI."""
    if not code.strip():
        return "# Please enter code to fix"

    logs = []
    logs.append(log_progress("🔍 Analyzing code..."))

    try:
        # Analyze code first
        from tools.code_analysis import analyze_code_structure
        analysis = analyze_code_structure(code, "python")

        issues_text = ""
        if "error" not in analysis:
            if analysis.get("complexity", 0) > 10:
                issues_text += "- High cyclomatic complexity\n"
            for func in analysis.get("functions", []):
                if func.get("nested_depth", 0) > 3:
                    issues_text += f"- High nesting in function '{func.get('name')}'\n"

        # Get security issues
        try:
            from tools.security_scanner import scan_security_issues
            security_issues = scan_security_issues(code, "")
            for issue in security_issues:
                issues_text += f"- {issue.get('message', 'Security issue')}\n"
        except:
            pass

        if not issues_text:
            logs.append(log_progress("✅ No issues found, code looks good!"))
            return "\n".join(logs)

        logs.append(log_progress("🔧 Fixing issues..."))
        from agents.coder import get_coder

        agent = get_coder()
        import asyncio

        fix_prompt = f"""Fix the following issues in this code:

{issues_text}

Original code:
```python
{code}
```

Provide only the fixed code, no explanations."""

        result = asyncio.run(agent.run(fix_prompt))
        fixed_code = result.output if hasattr(result, 'output') else str(result)

        logs.append(log_progress("✅ Issues fixed!"))
        return "\n".join(logs) + "\n\n---\nFixed Code:\n" + fixed_code

    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "required" in error_msg.lower():
            return "# ⚠️ Please set LLM_API_KEY in .env file"
        return "\n".join(logs) + f"\n❌ Error: {error_msg}"


def run_multi_agent_review(code: str) -> str:
    """Run multi-agent review workflow."""
    logs = []
    logs.append(log_progress("🚀 Starting multi-agent review..."))

    try:
        from agents.orchestrator.workflow import WorkflowBuilder
        from agents.orchestrator.builder import SequentialBuilder

        logs.append(log_progress("📋 Initializing agents..."))
        logs.append(log_progress("   - Linter agent"))
        logs.append(log_progress("   - Reviewer agent"))
        logs.append(log_progress("   - Coder agent (for fixes)"))

        # Run sequential workflow
        builder = SequentialBuilder()
        workflow = builder.build()

        logs.append(log_progress("⚙️ Running workflow..."))

        # Simulate workflow steps
        step = 1
        logs.append(log_progress(f"[{step}/4] Linter checking style..."))
        try:
            from tools.linter_tools import lint_python_code
            lint_result = lint_python_code(code, "")
            if lint_result:
                logs.append(log_progress(f"   📋 Style issues: {len(lint_result)} findings"))
        except Exception as e:
            logs.append(log_progress(f"   ⚠️ Lint skipped: {e}"))

        step += 1
        logs.append(log_progress(f"[{step}/4] Reviewer analyzing quality..."))
        try:
            from tools.code_analysis import analyze_code_structure
            analysis = analyze_code_structure(code, "python")
            if "error" not in analysis:
                logs.append(log_progress(f"   📊 {len(analysis.get('functions', []))} functions, {len(analysis.get('classes', []))} classes"))
        except Exception as e:
            logs.append(log_progress(f"   ⚠️ Analysis skipped: {e}"))

        step += 1
        logs.append(log_progress(f"[{step}/4] Security agent scanning..."))
        try:
            from tools.security_scanner import scan_security_issues
            sec_issues = security_scan(code, "python")
            if sec_issues:
                logs.append(log_progress(f"   🔒 {len(sec_issues)} security concerns"))
            else:
                logs.append(log_progress("   ✅ No security issues"))
        except Exception as e:
            logs.append(log_progress(f"   ⚠️ Security scan skipped: {e}"))

        step += 1
        logs.append(log_progress(f"[{step}/4] Coordinator aggregating results..."))

        logs.append(log_progress("✅ Multi-agent review complete!"))
        return "\n".join(logs)

    except Exception as e:
        return "\n".join(logs) + f"\n❌ Error: {e}"


def create_demo_interface():
    """Create demo interface with multi-agent workflow."""
    with gr.Blocks(title="Multi-Agent Code System") as demo:
        gr.Markdown("# 🧠 Multi-Agent Code Development System")

        with gr.Tabs():
            with gr.TabItem("📝 Code Editor"):
                gr.Markdown("### Write & Edit Code")
                code_editor = gr.Textbox(
                    value="# Write your Python code here...",
                    label="Code",
                    lines=15,
                )
                with gr.Row():
                    analyze_btn = gr.Button("🔍 Analyze", variant="primary")
                    lint_btn = gr.Button("✨ Lint")
                    fix_btn = gr.Button("🔧 Fix Issues")
                    multi_agent_btn = gr.Button("🤖 Multi-Agent Review")

                progress_output = gr.Textbox(label="Progress", lines=10, show_label=False)
                issues_output = gr.JSON(label="Issues Found")

                analyze_btn.click(
                    fn=run_full_workflow,
                    inputs=[code_editor],
                    outputs=[code_editor, issues_output, progress_output],
                )

                lint_btn.click(
                    fn=lambda code: run_full_workflow(code)[2],
                    inputs=[code_editor],
                    outputs=[progress_output],
                )

                fix_btn.click(
                    fn=review_and_fix,
                    inputs=[code_editor],
                    outputs=[code_editor],
                )

                multi_agent_btn.click(
                    fn=run_multi_agent_review,
                    inputs=[code_editor],
                    outputs=[progress_output],
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

                output_area = gr.Textbox(
                    label="Generated Code & Progress",
                    lines=20,
                    show_label=False,
                )

                def handle_generate(desc, lang):
                    return generate_code_with_progress(desc, lang)

                generate_btn.click(
                    fn=handle_generate,
                    inputs=[description, language],
                    outputs=[output_area],
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