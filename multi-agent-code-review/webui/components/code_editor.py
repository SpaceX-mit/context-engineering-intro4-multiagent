"""Code editor component for Gradio interface."""

from typing import Tuple, Optional

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    gr = None
    GRADIO_AVAILABLE = False


def create_code_editor_component() -> Tuple:
    """
    Create the code editor component.

    Returns:
        Tuple of (file_selector, code_editor, run_button)
    """
    if gr is None:
        raise ImportError("Gradio is not installed. Run: pip install gradio")

    file_selector = gr.Dropdown(
        label="Select File",
        choices=[],
        allow_custom_value=True,
    )

    code_editor = gr.Code(
        value="# Welcome to Code Editor\n# Select a file or enter code here",
        language="python",
        label="Code Editor",
        lines=20,
    )

    with gr.Row():
        save_btn = gr.Button("Save", variant="primary")
        run_btn = gr.Button("Run Agent")
        clear_btn = gr.Button("Clear")

    return file_selector, code_editor, save_btn, run_btn, clear_btn


def update_code_language(filename: str) -> str:
    """
    Determine language from file extension.

    Args:
        filename: Name of the file

    Returns:
        Language identifier for highlighting
    """
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".md": "markdown",
        ".sql": "sql",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sh": "bash",
    }

    import os
    _, ext = os.path.splitext(filename)
    return ext_map.get(ext.lower(), "text")


class CodeEditorManager:
    """Manager for code editor operations."""

    def __init__(self):
        self.current_file: Optional[str] = None
        self.modified: bool = False
        self.files: dict = {}

    def load_file(self, filepath: str) -> str:
        """
        Load a file into the editor.

        Args:
            filepath: Path to the file

        Returns:
            File content
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.current_file = filepath
            self.modified = False
            return content
        except Exception as e:
            return f"# Error loading file: {e}"

    def save_file(self, filepath: str, content: str) -> str:
        """
        Save content to a file.

        Args:
            filepath: Path to save to
            content: Content to save

        Returns:
            Status message
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file = filepath
            self.modified = False
            return f"Saved to {filepath}"
        except Exception as e:
            return f"Error saving file: {e}"

    def new_file(self, filename: str, content: str = "") -> str:
        """
        Create a new file.

        Args:
            filename: Name for the new file
            content: Initial content

        Returns:
            Status message
        """
        self.files[filename] = content
        self.current_file = filename
        return f"Created new file: {filename}"

    def is_modified(self) -> bool:
        """Check if current file is modified."""
        return self.modified

    def get_current_file(self) -> Optional[str]:
        """Get the current file path."""
        return self.current_file


# Global code editor manager
code_editor_manager = CodeEditorManager()
